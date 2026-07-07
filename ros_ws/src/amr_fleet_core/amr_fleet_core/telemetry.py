"""Fleet telemetry projections and audit events.

The telemetry layer is intentionally read-only with respect to the mission
domain. Adapters can publish these projections through ROS topics, HTTP JSON,
MQTT, OPC UA companion diagnostics, or dashboard exporters without gaining
permission to mutate safety-relevant state.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from .fleet import FleetService
from .mission import Mission
from .models import MissionState, Pose2D, RobotHealth, RobotSnapshot
from .station import StationLease


@dataclass(frozen=True, slots=True)
class TelemetryEvent:
    sequence: int
    timestamp: float
    event_type: str
    source: str
    severity: str
    payload: dict[str, Any]


class InMemoryTelemetrySink:
    """Append-only event sink used by tests, demos, and simple adapters."""

    def __init__(self) -> None:
        self._events: list[TelemetryEvent] = []

    def record(
        self,
        *,
        timestamp: float,
        event_type: str,
        source: str,
        payload: dict[str, Any] | None = None,
        severity: str = "info",
    ) -> TelemetryEvent:
        if not math.isfinite(timestamp):
            raise ValueError("timestamp must be finite")
        if not event_type.strip():
            raise ValueError("event_type must be non-empty")
        if not source.strip():
            raise ValueError("source must be non-empty")
        if not severity.strip():
            raise ValueError("severity must be non-empty")
        event = TelemetryEvent(
            sequence=len(self._events),
            timestamp=timestamp,
            event_type=event_type,
            source=source,
            severity=severity,
            payload=dict(payload or {}),
        )
        self._events.append(event)
        return event

    @property
    def events(self) -> tuple[TelemetryEvent, ...]:
        return tuple(self._events)

    def as_dicts(self) -> list[dict[str, Any]]:
        return [
            {
                "sequence": event.sequence,
                "timestamp": event.timestamp,
                "event_type": event.event_type,
                "source": event.source,
                "severity": event.severity,
                "payload": event.payload,
            }
            for event in self._events
        ]


@dataclass(frozen=True, slots=True)
class RobotTelemetry:
    robot_id: str
    pose: Pose2D
    battery_percent: float
    health: RobotHealth
    available: bool
    telemetry_at: float
    telemetry_age_seconds: float
    stale: bool


@dataclass(frozen=True, slots=True)
class MissionTelemetry:
    mission_id: str
    state: MissionState
    revision: int
    robot_id: str | None
    current_stop_index: int
    current_station_id: str
    current_waypoint: str
    station_lease_id: str | None
    recovery_attempts: int
    failure_reason: str | None


@dataclass(frozen=True, slots=True)
class FleetTelemetrySnapshot:
    generated_at: float
    robots: tuple[RobotTelemetry, ...]
    missions: tuple[MissionTelemetry, ...]
    station_leases: tuple[StationLease, ...]
    active_mission_by_robot: dict[str, str]
    stale_robot_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "robots": [
                {
                    "robot_id": robot.robot_id,
                    "pose": pose_to_dict(robot.pose),
                    "battery_percent": robot.battery_percent,
                    "health": robot.health.value,
                    "available": robot.available,
                    "telemetry_at": robot.telemetry_at,
                    "telemetry_age_seconds": robot.telemetry_age_seconds,
                    "stale": robot.stale,
                }
                for robot in self.robots
            ],
            "missions": [
                {
                    "mission_id": mission.mission_id,
                    "state": mission.state.value,
                    "revision": mission.revision,
                    "robot_id": mission.robot_id,
                    "current_stop_index": mission.current_stop_index,
                    "current_station_id": mission.current_station_id,
                    "current_waypoint": mission.current_waypoint,
                    "station_lease_id": mission.station_lease_id,
                    "recovery_attempts": mission.recovery_attempts,
                    "failure_reason": mission.failure_reason,
                }
                for mission in self.missions
            ],
            "station_leases": [
                {
                    "lease_id": lease.lease_id,
                    "station_id": lease.station_id,
                    "robot_id": lease.robot_id,
                    "mission_id": lease.mission_id,
                    "granted_at": lease.granted_at,
                    "expires_at": lease.expires_at,
                }
                for lease in self.station_leases
            ],
            "active_mission_by_robot": dict(self.active_mission_by_robot),
            "stale_robot_ids": list(self.stale_robot_ids),
        }


def pose_to_dict(pose: Pose2D) -> dict[str, float | str]:
    return {
        "x": pose.x,
        "y": pose.y,
        "yaw": pose.yaw,
        "frame_id": pose.frame_id,
    }


def mission_to_telemetry(mission: Mission) -> MissionTelemetry:
    current_stop = mission.current_stop
    return MissionTelemetry(
        mission_id=mission.mission_id,
        state=mission.state,
        revision=mission.revision,
        robot_id=mission.robot_id,
        current_stop_index=mission.current_stop_index,
        current_station_id=current_stop.station_id,
        current_waypoint=current_stop.waypoint,
        station_lease_id=mission.station_lease_id,
        recovery_attempts=mission.recovery_attempts,
        failure_reason=mission.failure_reason,
    )


def robot_to_telemetry(
    robot: RobotSnapshot,
    *,
    now: float,
    telemetry_stale_after: float,
) -> RobotTelemetry:
    if telemetry_stale_after <= 0.0:
        raise ValueError("telemetry_stale_after must be positive")
    age = max(0.0, now - robot.telemetry_at)
    return RobotTelemetry(
        robot_id=robot.robot_id,
        pose=robot.pose,
        battery_percent=robot.battery_percent,
        health=robot.health,
        available=robot.available,
        telemetry_at=robot.telemetry_at,
        telemetry_age_seconds=age,
        stale=age > telemetry_stale_after,
    )


def project_fleet_telemetry(
    service: FleetService,
    *,
    now: float,
    telemetry_stale_after: float,
) -> FleetTelemetrySnapshot:
    robots = tuple(
        robot_to_telemetry(
            robot,
            now=now,
            telemetry_stale_after=telemetry_stale_after,
        )
        for robot in service.robots()
    )
    stale_robot_ids = tuple(robot.robot_id for robot in robots if robot.stale)
    return FleetTelemetrySnapshot(
        generated_at=now,
        robots=robots,
        missions=tuple(mission_to_telemetry(mission) for mission in service.missions()),
        station_leases=service.active_station_leases(now=now),
        active_mission_by_robot=service.active_mission_by_robot(),
        stale_robot_ids=stale_robot_ids,
    )
