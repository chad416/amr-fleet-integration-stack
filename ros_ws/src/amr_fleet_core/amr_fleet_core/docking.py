"""Deterministic pseudo-docking controller for simulation and commissioning."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math

from .models import Pose2D


class DockingPhase(str, Enum):
    HOLD = "hold"
    ALIGN = "align"
    APPROACH = "approach"
    FINAL_ALIGN = "final_align"
    DOCKED = "docked"


@dataclass(frozen=True, slots=True)
class DockingCommand:
    phase: DockingPhase
    linear_x: float
    angular_z: float
    position_error: float
    yaw_error: float


class PseudoDockingController:
    """Generate bounded planar commands while station authorization remains valid."""

    def __init__(
        self,
        *,
        position_tolerance: float = 0.05,
        yaw_tolerance: float = math.radians(3.0),
        max_linear_speed: float = 0.12,
        max_angular_speed: float = 0.40,
        alignment_threshold: float = math.radians(12.0),
    ) -> None:
        values = (
            position_tolerance,
            yaw_tolerance,
            max_linear_speed,
            max_angular_speed,
            alignment_threshold,
        )
        if any(value <= 0.0 or not math.isfinite(value) for value in values):
            raise ValueError("docking limits must be positive and finite")
        self.position_tolerance = position_tolerance
        self.yaw_tolerance = yaw_tolerance
        self.max_linear_speed = max_linear_speed
        self.max_angular_speed = max_angular_speed
        self.alignment_threshold = alignment_threshold

    def command(
        self,
        current: Pose2D,
        target: Pose2D,
        *,
        station_authorized: bool,
    ) -> DockingCommand:
        distance = current.distance_to(target)
        final_yaw_error = _normalize_angle(target.yaw - current.yaw)
        if not station_authorized:
            return DockingCommand(DockingPhase.HOLD, 0.0, 0.0, distance, final_yaw_error)
        if distance <= self.position_tolerance:
            if abs(final_yaw_error) <= self.yaw_tolerance:
                return DockingCommand(
                    DockingPhase.DOCKED,
                    0.0,
                    0.0,
                    distance,
                    final_yaw_error,
                )
            return DockingCommand(
                DockingPhase.FINAL_ALIGN,
                0.0,
                _clamp(1.5 * final_yaw_error, self.max_angular_speed),
                distance,
                final_yaw_error,
            )

        target_heading = math.atan2(target.y - current.y, target.x - current.x)
        heading_error = _normalize_angle(target_heading - current.yaw)
        if abs(heading_error) > self.alignment_threshold:
            return DockingCommand(
                DockingPhase.ALIGN,
                0.0,
                _clamp(1.5 * heading_error, self.max_angular_speed),
                distance,
                heading_error,
            )
        return DockingCommand(
            DockingPhase.APPROACH,
            min(self.max_linear_speed, max(0.02, 0.8 * distance)),
            _clamp(1.2 * heading_error, self.max_angular_speed),
            distance,
            heading_error,
        )


def _normalize_angle(value: float) -> float:
    return math.atan2(math.sin(value), math.cos(value))


def _clamp(value: float, limit: float) -> float:
    return max(-limit, min(limit, value))
