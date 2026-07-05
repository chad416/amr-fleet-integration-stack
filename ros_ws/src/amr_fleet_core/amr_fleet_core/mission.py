"""Mission aggregate and lifecycle invariants."""

from __future__ import annotations

from dataclasses import dataclass

from .errors import InvalidTransition
from .models import MissionState, MissionStop


@dataclass(frozen=True, slots=True)
class MissionEvent:
    sequence: int
    previous: MissionState | None
    current: MissionState
    detail: str


class Mission:
    """Mutable aggregate whose commands enforce the documented mission lifecycle."""

    def __init__(self, mission_id: str, stops: tuple[MissionStop, ...]) -> None:
        if not mission_id.strip():
            raise ValueError("mission_id must be non-empty")
        if not stops:
            raise ValueError("a mission requires at least one stop")
        self.mission_id = mission_id
        self.stops = stops
        self.state = MissionState.QUEUED
        self.robot_id: str | None = None
        self.current_stop_index = 0
        self.station_lease_id: str | None = None
        self.failure_reason: str | None = None
        self._paused_from: MissionState | None = None
        self._events = [MissionEvent(0, None, MissionState.QUEUED, "mission submitted")]

    @property
    def current_stop(self) -> MissionStop:
        return self.stops[self.current_stop_index]

    @property
    def events(self) -> tuple[MissionEvent, ...]:
        return tuple(self._events)

    @property
    def revision(self) -> int:
        return self._events[-1].sequence

    def assign(self, robot_id: str) -> None:
        self._require(MissionState.QUEUED)
        if not robot_id.strip():
            raise ValueError("robot_id must be non-empty")
        self.robot_id = robot_id
        self._transition(MissionState.DISPATCHED, f"assigned to {robot_id}")

    def start(self) -> None:
        self._require(MissionState.DISPATCHED)
        if self.robot_id is None:
            raise InvalidTransition("mission has no robot assignment")
        self._transition(MissionState.NAVIGATING, "execution started")

    def arrive_at_station_approach(self) -> None:
        self._require(MissionState.NAVIGATING)
        self._transition(
            MissionState.AWAITING_STATION,
            f"approach reached for {self.current_stop.station_id}",
        )

    def grant_station_access(self, lease_id: str) -> None:
        self._require(MissionState.AWAITING_STATION)
        if not lease_id.strip():
            raise ValueError("lease_id must be non-empty")
        self.station_lease_id = lease_id
        self._record("station access granted")

    def start_docking(self, lease_id: str) -> None:
        self._require(MissionState.AWAITING_STATION)
        self._require_matching_lease(lease_id)
        self._transition(MissionState.DOCKING, "docking started")

    def confirm_docked(self, lease_id: str) -> None:
        self._require(MissionState.DOCKING)
        self._require_matching_lease(lease_id)
        self._transition(MissionState.TRANSFERRING, "dock confirmed; transfer started")

    def complete_transfer(self, lease_id: str) -> None:
        self._require(MissionState.TRANSFERRING)
        self._require_matching_lease(lease_id)
        self.station_lease_id = None
        if self.current_stop_index + 1 == len(self.stops):
            self._transition(MissionState.COMPLETED, "final transfer complete")
            return
        self.current_stop_index += 1
        self._transition(MissionState.NAVIGATING, "transfer complete; navigating to next stop")

    def pause(self) -> None:
        if self.state not in {MissionState.NAVIGATING, MissionState.AWAITING_STATION}:
            self._raise_invalid("pause")
        self._paused_from = self.state
        self._transition(MissionState.PAUSED, "operator pause")

    def resume(self) -> None:
        self._require(MissionState.PAUSED)
        if self._paused_from is None:
            raise InvalidTransition("paused mission has no resumable state")
        target = self._paused_from
        self._paused_from = None
        self._transition(target, "operator resume")

    def cancel(self, reason: str) -> None:
        self._require_nonterminal("cancel")
        self.station_lease_id = None
        self._transition(MissionState.CANCELED, reason or "mission canceled")

    def fail(self, reason: str) -> None:
        self._require_nonterminal("fail")
        if not reason.strip():
            raise ValueError("failure reason must be non-empty")
        self.failure_reason = reason
        self.station_lease_id = None
        self._transition(MissionState.FAILED, reason)

    def _require_matching_lease(self, lease_id: str) -> None:
        if self.station_lease_id is None:
            raise InvalidTransition("station access has not been granted")
        if lease_id != self.station_lease_id:
            raise InvalidTransition("station lease does not match the mission")

    def _require(self, expected: MissionState) -> None:
        if self.state is not expected:
            raise InvalidTransition(f"expected {expected.value}, found {self.state.value}")

    def _require_nonterminal(self, command: str) -> None:
        if self.state.terminal:
            self._raise_invalid(command)

    def _raise_invalid(self, command: str) -> None:
        raise InvalidTransition(f"cannot {command} mission in {self.state.value}")

    def _transition(self, target: MissionState, detail: str) -> None:
        previous = self.state
        self.state = target
        self._events.append(MissionEvent(self.revision + 1, previous, target, detail))

    def _record(self, detail: str) -> None:
        self._events.append(MissionEvent(self.revision + 1, self.state, self.state, detail))
