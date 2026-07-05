"""Application service coordinating missions, dispatch, and station access."""

from __future__ import annotations

from .dispatch import NearestEligibleDispatcher
from .errors import DuplicateMissionConflict, NotFound
from .mission import Mission
from .models import MissionStop, RobotSnapshot
from .station import StationAccessManager, StationLease


class FleetService:
    def __init__(
        self,
        dispatcher: NearestEligibleDispatcher,
        station_access: StationAccessManager,
    ) -> None:
        self._dispatcher = dispatcher
        self._station_access = station_access
        self._robots: dict[str, RobotSnapshot] = {}
        self._missions: dict[str, Mission] = {}
        self._active_mission_by_robot: dict[str, str] = {}

    def update_robot(self, snapshot: RobotSnapshot) -> None:
        previous = self._robots.get(snapshot.robot_id)
        if previous is not None and snapshot.telemetry_at < previous.telemetry_at:
            return
        self._robots[snapshot.robot_id] = snapshot

    def submit_mission(self, mission_id: str, stops: tuple[MissionStop, ...]) -> Mission:
        current = self._missions.get(mission_id)
        if current is not None:
            if current.stops != stops:
                raise DuplicateMissionConflict(
                    f"mission {mission_id} already exists with a different payload"
                )
            return current
        mission = Mission(mission_id, stops)
        self._missions[mission_id] = mission
        return mission

    def mission(self, mission_id: str) -> Mission:
        try:
            return self._missions[mission_id]
        except KeyError as error:
            raise NotFound(f"unknown mission: {mission_id}") from error

    def dispatch(self, mission_id: str, *, now: float) -> str:
        mission = self.mission(mission_id)
        robot = self._dispatcher.select(
            self._robots.values(),
            mission.current_stop,
            now=now,
            busy_robot_ids=self._active_mission_by_robot.keys(),
        )
        mission.assign(robot.robot_id)
        self._active_mission_by_robot[robot.robot_id] = mission_id
        return robot.robot_id

    def start(self, mission_id: str) -> None:
        self.mission(mission_id).start()

    def arrive_at_station_approach(self, mission_id: str) -> None:
        self.mission(mission_id).arrive_at_station_approach()

    def request_station_access(self, mission_id: str, *, now: float) -> StationLease:
        mission = self.mission(mission_id)
        if mission.robot_id is None:
            raise RuntimeError("assigned mission invariant violated")
        lease = self._station_access.acquire(
            mission.current_stop.station_id,
            mission.robot_id,
            mission.mission_id,
            now=now,
        )
        mission.grant_station_access(lease.lease_id)
        return lease

    def start_docking(self, mission_id: str, lease_id: str, *, now: float) -> None:
        mission = self.mission(mission_id)
        self._validate_lease(mission, lease_id, now=now)
        mission.start_docking(lease_id)

    def confirm_docked(self, mission_id: str, lease_id: str, *, now: float) -> None:
        mission = self.mission(mission_id)
        self._validate_lease(mission, lease_id, now=now)
        mission.confirm_docked(lease_id)

    def complete_transfer(self, mission_id: str, lease_id: str, *, now: float) -> None:
        mission = self.mission(mission_id)
        self._validate_lease(mission, lease_id, now=now)
        station_id = mission.current_stop.station_id
        self._station_access.release(station_id, lease_id, now=now)
        mission.complete_transfer(lease_id)
        if mission.state.terminal:
            self._release_robot(mission)

    def pause(self, mission_id: str) -> None:
        self.mission(mission_id).pause()

    def resume(self, mission_id: str) -> None:
        self.mission(mission_id).resume()

    def cancel(self, mission_id: str, reason: str, *, now: float) -> None:
        mission = self.mission(mission_id)
        self._release_lease_if_present(mission, now=now)
        mission.cancel(reason)
        self._release_robot(mission)

    def fail(self, mission_id: str, reason: str, *, now: float) -> None:
        mission = self.mission(mission_id)
        self._release_lease_if_present(mission, now=now)
        mission.fail(reason)
        self._release_robot(mission)

    def _validate_lease(self, mission: Mission, lease_id: str, *, now: float) -> None:
        if mission.robot_id is None:
            raise RuntimeError("assigned mission invariant violated")
        self._station_access.validate(
            mission.current_stop.station_id,
            lease_id,
            mission.robot_id,
            mission.mission_id,
            now=now,
        )

    def _release_lease_if_present(self, mission: Mission, *, now: float) -> None:
        if mission.station_lease_id is not None:
            self._station_access.release(
                mission.current_stop.station_id,
                mission.station_lease_id,
                now=now,
            )

    def _release_robot(self, mission: Mission) -> None:
        if mission.robot_id is not None:
            self._active_mission_by_robot.pop(mission.robot_id, None)
