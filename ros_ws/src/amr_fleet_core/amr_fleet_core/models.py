"""Shared immutable value objects and enumerations."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum


class MissionState(str, Enum):
    QUEUED = "queued"
    DISPATCHED = "dispatched"
    NAVIGATING = "navigating"
    AWAITING_STATION = "awaiting_station"
    DOCKING = "docking"
    TRANSFERRING = "transferring"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELED = "canceled"
    FAILED = "failed"

    @property
    def terminal(self) -> bool:
        return self in {self.COMPLETED, self.CANCELED, self.FAILED}


class RobotHealth(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAULT = "fault"
    EMERGENCY_STOPPED = "emergency_stopped"
    OFFLINE = "offline"


@dataclass(frozen=True, slots=True)
class Pose2D:
    x: float
    y: float
    yaw: float = 0.0
    frame_id: str = "map"

    def __post_init__(self) -> None:
        if not self.frame_id.strip():
            raise ValueError("frame_id must be non-empty")
        if not all(math.isfinite(value) for value in (self.x, self.y, self.yaw)):
            raise ValueError("pose values must be finite")

    def distance_to(self, other: Pose2D) -> float:
        if self.frame_id != other.frame_id:
            raise ValueError("cannot compare poses in different frames")
        return math.hypot(self.x - other.x, self.y - other.y)


@dataclass(frozen=True, slots=True)
class MissionStop:
    station_id: str
    waypoint: str
    approach_pose: Pose2D

    def __post_init__(self) -> None:
        if not self.station_id.strip():
            raise ValueError("station_id must be non-empty")
        if not self.waypoint.strip():
            raise ValueError("waypoint must be non-empty")


@dataclass(frozen=True, slots=True)
class RobotSnapshot:
    robot_id: str
    pose: Pose2D
    battery_percent: float
    health: RobotHealth
    available: bool
    telemetry_at: float

    def __post_init__(self) -> None:
        if not self.robot_id.strip():
            raise ValueError("robot_id must be non-empty")
        if not 0.0 <= self.battery_percent <= 100.0:
            raise ValueError("battery_percent must be in [0, 100]")
        if not math.isfinite(self.telemetry_at):
            raise ValueError("telemetry_at must be finite")

    def is_dispatch_eligible(
        self,
        *,
        now: float,
        stale_after: float,
        minimum_battery: float,
        reject_degraded: bool,
    ) -> bool:
        age = max(0.0, now - self.telemetry_at)
        allowed_health = {RobotHealth.HEALTHY}
        if not reject_degraded:
            allowed_health.add(RobotHealth.DEGRADED)
        return (
            self.available
            and age <= stale_after
            and self.battery_percent >= minimum_battery
            and self.health in allowed_health
        )
