"""Battery-aware charge mission policy."""

from __future__ import annotations

from dataclasses import dataclass

from .models import MissionStop, Pose2D, RobotHealth, RobotSnapshot


@dataclass(frozen=True, slots=True)
class ChargeMissionRequest:
    mission_id: str
    robot_id: str
    stop: MissionStop
    reason: str


class ChargePolicy:
    """Select robots that should be routed to a charger before more work."""

    def __init__(
        self,
        *,
        critical_battery_percent: float,
        charger_station_id: str,
        charger_waypoint: str,
        charger_pose: Pose2D,
    ) -> None:
        if not 0.0 <= critical_battery_percent <= 100.0:
            raise ValueError("critical_battery_percent must be in [0, 100]")
        if not charger_station_id.strip():
            raise ValueError("charger_station_id must be non-empty")
        if not charger_waypoint.strip():
            raise ValueError("charger_waypoint must be non-empty")
        self.critical_battery_percent = critical_battery_percent
        self.charger_station_id = charger_station_id
        self.charger_waypoint = charger_waypoint
        self.charger_pose = charger_pose

    def requires_charge(self, robot: RobotSnapshot) -> bool:
        return (
            robot.available
            and robot.health in {RobotHealth.HEALTHY, RobotHealth.DEGRADED}
            and robot.battery_percent <= self.critical_battery_percent
        )

    def robots_requiring_charge(
        self,
        robots: tuple[RobotSnapshot, ...],
    ) -> tuple[RobotSnapshot, ...]:
        return tuple(
            sorted(
                (robot for robot in robots if self.requires_charge(robot)),
                key=lambda robot: (robot.battery_percent, robot.robot_id),
            )
        )

    def charge_mission_for(self, robot: RobotSnapshot, *, sequence: int) -> ChargeMissionRequest:
        if sequence < 0:
            raise ValueError("sequence cannot be negative")
        stop = MissionStop(
            station_id=self.charger_station_id,
            waypoint=self.charger_waypoint,
            approach_pose=self.charger_pose,
        )
        return ChargeMissionRequest(
            mission_id=f"charge-{robot.robot_id}-{sequence:04d}",
            robot_id=robot.robot_id,
            stop=stop,
            reason=(
                f"battery {robot.battery_percent:.1f}% <= "
                f"{self.critical_battery_percent:.1f}%"
            ),
        )
