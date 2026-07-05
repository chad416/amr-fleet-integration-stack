"""Deterministic robot allocation policy."""

from __future__ import annotations

from collections.abc import Iterable, Set

from .errors import NoEligibleRobot
from .models import MissionStop, RobotSnapshot


class NearestEligibleDispatcher:
    """Select the nearest eligible robot with a stable robot-ID tie breaker."""

    def __init__(
        self,
        *,
        minimum_battery: float,
        telemetry_stale_after: float,
        reject_degraded: bool = True,
    ) -> None:
        if not 0.0 <= minimum_battery <= 100.0:
            raise ValueError("minimum_battery must be in [0, 100]")
        if telemetry_stale_after <= 0.0:
            raise ValueError("telemetry_stale_after must be positive")
        self.minimum_battery = minimum_battery
        self.telemetry_stale_after = telemetry_stale_after
        self.reject_degraded = reject_degraded

    def select(
        self,
        robots: Iterable[RobotSnapshot],
        first_stop: MissionStop,
        *,
        now: float,
        busy_robot_ids: Set[str] = frozenset(),
    ) -> RobotSnapshot:
        eligible = (
            robot
            for robot in robots
            if robot.robot_id not in busy_robot_ids
            and robot.is_dispatch_eligible(
                now=now,
                stale_after=self.telemetry_stale_after,
                minimum_battery=self.minimum_battery,
                reject_degraded=self.reject_degraded,
            )
        )
        ranked = sorted(
            eligible,
            key=lambda robot: (robot.pose.distance_to(first_stop.approach_pose), robot.robot_id),
        )
        if not ranked:
            raise NoEligibleRobot("no robot satisfies health, freshness, battery, and availability")
        return ranked[0]
