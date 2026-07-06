"""Transport-independent remote mission API facade."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from .alarms import FleetAlarmEvaluator
from .dispatch import NearestEligibleDispatcher
from .errors import DomainError
from .fleet import FleetService
from .models import MissionStop, Pose2D, RobotHealth, RobotSnapshot
from .station import StationAccessManager
from .telemetry import (
    InMemoryTelemetrySink,
    pose_to_dict,
    project_fleet_telemetry,
)
from .waypoints import WaypointCatalog


Clock = Callable[[], float]


@dataclass(frozen=True, slots=True)
class ApiResponse:
    ok: bool
    status: int
    body: dict[str, Any]


class FleetApi:
    """Boundary facade used by ROS actions, HTTP, CLI, and future MQTT adapters."""

    def __init__(
        self,
        service: FleetService,
        *,
        telemetry_stale_after: float,
        clock: Clock | None = None,
        telemetry_sink: InMemoryTelemetrySink | None = None,
        waypoint_catalog: WaypointCatalog | None = None,
        alarm_evaluator: FleetAlarmEvaluator | None = None,
    ) -> None:
        if telemetry_stale_after <= 0.0:
            raise ValueError("telemetry_stale_after must be positive")
        self.service = service
        self.telemetry_stale_after = telemetry_stale_after
        self._clock = clock or time.monotonic
        self.telemetry_sink = telemetry_sink or InMemoryTelemetrySink()
        self.waypoint_catalog = waypoint_catalog
        self.alarm_evaluator = alarm_evaluator or FleetAlarmEvaluator()

    def update_robot(self, payload: dict[str, Any]) -> ApiResponse:
        return self._execute(
            "robot.telemetry",
            lambda: self._update_robot(payload),
            payload={"robot_id": payload.get("robot_id")},
        )

    def submit_mission(self, payload: dict[str, Any]) -> ApiResponse:
        return self._execute(
            "mission.submit",
            lambda: self._submit_mission(payload),
            payload={"mission_id": payload.get("mission_id")},
            success_status=201,
        )

    def dispatch(self, mission_id: str, payload: dict[str, Any]) -> ApiResponse:
        return self._execute(
            "mission.dispatch",
            lambda: self._dispatch(mission_id, payload),
            payload={"mission_id": mission_id},
        )

    def dispatch_all(self, payload: dict[str, Any]) -> ApiResponse:
        return self._execute(
            "fleet.dispatch_all",
            lambda: self._dispatch_all(payload),
            payload={"queued_only": True},
        )

    def start(self, mission_id: str) -> ApiResponse:
        return self._mission_command(
            "mission.start",
            mission_id,
            lambda: self.service.start(mission_id),
        )

    def arrive_at_station_approach(self, mission_id: str) -> ApiResponse:
        return self._mission_command(
            "mission.arrive_at_station_approach",
            mission_id,
            lambda: self.service.arrive_at_station_approach(mission_id),
        )

    def request_station_access(self, mission_id: str, payload: dict[str, Any]) -> ApiResponse:
        return self._execute(
            "station.request_access",
            lambda: self._request_station_access(mission_id, payload),
            payload={"mission_id": mission_id},
        )

    def start_docking(self, mission_id: str, payload: dict[str, Any]) -> ApiResponse:
        return self._lease_command(
            "mission.start_docking",
            mission_id,
            payload,
            self.service.start_docking,
        )

    def confirm_docked(self, mission_id: str, payload: dict[str, Any]) -> ApiResponse:
        return self._lease_command(
            "mission.confirm_docked",
            mission_id,
            payload,
            self.service.confirm_docked,
        )

    def complete_transfer(self, mission_id: str, payload: dict[str, Any]) -> ApiResponse:
        return self._lease_command(
            "mission.complete_transfer",
            mission_id,
            payload,
            self.service.complete_transfer,
        )

    def pause(self, mission_id: str) -> ApiResponse:
        return self._mission_command(
            "mission.pause",
            mission_id,
            lambda: self.service.pause(mission_id),
        )

    def resume(self, mission_id: str) -> ApiResponse:
        return self._mission_command(
            "mission.resume",
            mission_id,
            lambda: self.service.resume(mission_id),
        )

    def cancel(self, mission_id: str, payload: dict[str, Any]) -> ApiResponse:
        return self._execute(
            "mission.cancel",
            lambda: self._cancel(mission_id, payload),
            payload={"mission_id": mission_id},
        )

    def begin_recovery(self, mission_id: str, payload: dict[str, Any]) -> ApiResponse:
        return self._execute(
            "mission.recovery.begin",
            lambda: self._begin_recovery(mission_id, payload),
            payload={"mission_id": mission_id},
        )

    def complete_recovery(self, mission_id: str) -> ApiResponse:
        return self._mission_command(
            "mission.recovery.complete",
            mission_id,
            lambda: self.service.complete_recovery(mission_id),
        )

    def mission(self, mission_id: str) -> ApiResponse:
        try:
            return ApiResponse(
                True,
                200,
                {"mission": mission_to_dict(self.service.mission(mission_id))},
            )
        except DomainError as error:
            return self._error_response(error)

    def telemetry(self, *, now: float | None = None) -> ApiResponse:
        timestamp = self._time_from_payload({"now": now} if now is not None else {})
        snapshot = project_fleet_telemetry(
            self.service,
            now=timestamp,
            telemetry_stale_after=self.telemetry_stale_after,
        )
        alarms = self.alarm_evaluator.evaluate(snapshot)
        return ApiResponse(
            True,
            200,
            {
                "fleet": snapshot.to_dict(),
                "events": self.telemetry_sink.as_dicts(),
                "alarms": [alarm.to_dict() for alarm in alarms],
            },
        )

    def _update_robot(self, payload: dict[str, Any]) -> dict[str, Any]:
        pose_payload = _require_dict(payload, "pose")
        snapshot = RobotSnapshot(
            robot_id=_require_string(payload, "robot_id"),
            pose=_pose_from_payload(pose_payload),
            battery_percent=float(payload["battery_percent"]),
            health=RobotHealth(str(payload["health"])),
            available=bool(payload["available"]),
            telemetry_at=float(payload["telemetry_at"]),
        )
        self.service.update_robot(snapshot)
        return {"robot": robot_to_dict(snapshot)}

    def _submit_mission(self, payload: dict[str, Any]) -> dict[str, Any]:
        mission_id = _require_string(payload, "mission_id")
        stops_payload = payload.get("stops")
        if not isinstance(stops_payload, list):
            raise ValueError("stops must be a list")
        stops = tuple(self._stop_from_payload(stop) for stop in stops_payload)
        mission = self.service.submit_mission(mission_id, stops)
        return {"mission": mission_to_dict(mission)}

    def _dispatch(self, mission_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        robot_id = self.service.dispatch(
            mission_id,
            now=self._time_from_payload(payload),
        )
        return {"mission": mission_to_dict(self.service.mission(mission_id)), "robot_id": robot_id}

    def _dispatch_all(self, payload: dict[str, Any]) -> dict[str, Any]:
        assignments = self.service.dispatch_all(now=self._time_from_payload(payload))
        return {
            "assignments": [
                {"mission_id": mission_id, "robot_id": robot_id}
                for mission_id, robot_id in assignments
            ],
            "missions": [mission_to_dict(mission) for mission in self.service.missions()],
        }

    def _request_station_access(self, mission_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        lease = self.service.request_station_access(
            mission_id,
            now=self._time_from_payload(payload),
        )
        return {
            "mission": mission_to_dict(self.service.mission(mission_id)),
            "lease": {
                "lease_id": lease.lease_id,
                "station_id": lease.station_id,
                "robot_id": lease.robot_id,
                "mission_id": lease.mission_id,
                "granted_at": lease.granted_at,
                "expires_at": lease.expires_at,
            },
        }

    def _cancel(self, mission_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.service.cancel(
            mission_id,
            str(payload.get("reason", "operator canceled mission")),
            now=self._time_from_payload(payload),
        )
        return {"mission": mission_to_dict(self.service.mission(mission_id))}

    def _begin_recovery(self, mission_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        attempt = self.service.begin_recovery(
            mission_id,
            str(payload.get("reason", "autonomous recovery requested")),
            now=self._time_from_payload(payload),
        )
        return {"mission": mission_to_dict(self.service.mission(mission_id)), "attempt": attempt}

    def _stop_from_payload(self, payload: Any) -> MissionStop:
        if not isinstance(payload, dict):
            raise ValueError("each stop must be an object")
        station_id = _require_string(payload, "station_id")
        waypoint = _require_string(payload, "waypoint")
        approach_pose = payload.get("approach_pose")
        if approach_pose is None:
            if self.waypoint_catalog is None:
                raise ValueError(
                    "approach_pose is required when no waypoint catalog is configured"
                )
            return self.waypoint_catalog.resolve(station_id, waypoint)
        if not isinstance(approach_pose, dict):
            raise ValueError("approach_pose must be an object")
        return MissionStop(
            station_id=station_id,
            waypoint=waypoint,
            approach_pose=_pose_from_payload(approach_pose),
        )

    def _lease_command(
        self,
        event_type: str,
        mission_id: str,
        payload: dict[str, Any],
        command: Callable[[str, str], None],
    ) -> ApiResponse:
        def execute() -> dict[str, Any]:
            command(
                mission_id,
                _require_string(payload, "lease_id"),
                now=self._time_from_payload(payload),
            )
            return {"mission": mission_to_dict(self.service.mission(mission_id))}

        return self._execute(event_type, execute, payload={"mission_id": mission_id})

    def _mission_command(
        self,
        event_type: str,
        mission_id: str,
        command: Callable[[], None],
    ) -> ApiResponse:
        def execute() -> dict[str, Any]:
            command()
            return {"mission": mission_to_dict(self.service.mission(mission_id))}

        return self._execute(event_type, execute, payload={"mission_id": mission_id})

    def _execute(
        self,
        event_type: str,
        action: Callable[[], dict[str, Any]],
        *,
        payload: dict[str, Any],
        success_status: int = 200,
    ) -> ApiResponse:
        timestamp = self._clock()
        try:
            body = action()
            self.telemetry_sink.record(
                timestamp=timestamp,
                event_type=event_type,
                source="fleet_api",
                payload=payload,
            )
            return ApiResponse(True, success_status, body)
        except (DomainError, ValueError, TypeError, KeyError) as error:
            self.telemetry_sink.record(
                timestamp=timestamp,
                event_type=f"{event_type}.rejected",
                source="fleet_api",
                payload={**payload, "error": str(error)},
                severity="warning",
            )
            return self._error_response(error)

    def _error_response(self, error: Exception) -> ApiResponse:
        status = 400
        if error.__class__.__name__ == "NotFound":
            status = 404
        if error.__class__.__name__ in {"NoEligibleRobot", "StationBusy"}:
            status = 409
        if error.__class__.__name__ == "RecoveryLimitExceeded":
            status = 422
        return ApiResponse(
            False,
            status,
            {
                "error": {
                    "code": error.__class__.__name__,
                    "message": str(error),
                }
            },
        )

    def _time_from_payload(self, payload: dict[str, Any]) -> float:
        value = payload.get("now")
        if value is None:
            return self._clock()
        return float(value)


def create_fleet_api(
    *,
    station_ids: Iterable[str],
    minimum_battery: float = 30.0,
    telemetry_stale_after: float = 3.0,
    station_lease_seconds: float = 30.0,
    reject_degraded: bool = True,
    recovery_max_attempts: int = 3,
    clock: Clock | None = None,
    waypoint_catalog: WaypointCatalog | None = None,
) -> FleetApi:
    station_ids_set = set(station_ids)
    dispatcher = NearestEligibleDispatcher(
        minimum_battery=minimum_battery,
        telemetry_stale_after=telemetry_stale_after,
        reject_degraded=reject_degraded,
    )
    service = FleetService(
        dispatcher,
        StationAccessManager(station_ids_set, default_lease_seconds=station_lease_seconds),
        recovery_max_attempts=recovery_max_attempts,
    )
    return FleetApi(
        service,
        telemetry_stale_after=telemetry_stale_after,
        clock=clock,
        waypoint_catalog=waypoint_catalog,
    )


def mission_to_dict(mission: Any) -> dict[str, Any]:
    return {
        "mission_id": mission.mission_id,
        "state": mission.state.value,
        "robot_id": mission.robot_id,
        "current_stop_index": mission.current_stop_index,
        "current_stop": {
            "station_id": mission.current_stop.station_id,
            "waypoint": mission.current_stop.waypoint,
            "approach_pose": pose_to_dict(mission.current_stop.approach_pose),
        },
        "station_lease_id": mission.station_lease_id,
        "recovery_attempts": mission.recovery_attempts,
        "failure_reason": mission.failure_reason,
        "revision": mission.revision,
        "events": [
            {
                "sequence": event.sequence,
                "previous": event.previous.value if event.previous is not None else None,
                "current": event.current.value,
                "detail": event.detail,
            }
            for event in mission.events
        ],
    }


def robot_to_dict(robot: RobotSnapshot) -> dict[str, Any]:
    return {
        "robot_id": robot.robot_id,
        "pose": pose_to_dict(robot.pose),
        "battery_percent": robot.battery_percent,
        "health": robot.health.value,
        "available": robot.available,
        "telemetry_at": robot.telemetry_at,
    }


def _pose_from_payload(payload: dict[str, Any]) -> Pose2D:
    return Pose2D(
        x=float(payload["x"]),
        y=float(payload["y"]),
        yaw=float(payload.get("yaw", 0.0)),
        frame_id=str(payload.get("frame_id", "map")),
    )


def _require_dict(payload: dict[str, Any], field: str) -> dict[str, Any]:
    value = payload.get(field)
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    return value


def _require_string(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value
