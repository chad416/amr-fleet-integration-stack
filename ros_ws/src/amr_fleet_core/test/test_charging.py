"""Verification of battery-aware charging policy."""

import unittest

from amr_fleet_core import ChargePolicy, Pose2D, RobotHealth, RobotSnapshot


def robot(
    robot_id: str,
    battery: float,
    *,
    health: RobotHealth = RobotHealth.HEALTHY,
    available: bool = True,
) -> RobotSnapshot:
    return RobotSnapshot(
        robot_id=robot_id,
        pose=Pose2D(0.0, 0.0),
        battery_percent=battery,
        health=health,
        available=available,
        telemetry_at=100.0,
    )


class ChargePolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = ChargePolicy(
            critical_battery_percent=15.0,
            charger_station_id="charger_01",
            charger_waypoint="charger_01_approach",
            charger_pose=Pose2D(-4.5, 0.0, 3.14),
        )

    def test_low_battery_available_robots_are_selected_in_priority_order(self) -> None:
        selected = self.policy.robots_requiring_charge(
            (
                robot("amr-healthy-ok", 80.0),
                robot("amr-critical-b", 14.0),
                robot("amr-critical-a", 5.0),
                robot("amr-fault", 4.0, health=RobotHealth.FAULT),
                robot("amr-unavailable", 3.0, available=False),
            )
        )

        self.assertEqual(
            [item.robot_id for item in selected],
            ["amr-critical-a", "amr-critical-b"],
        )

    def test_charge_mission_request_targets_configured_charger(self) -> None:
        request = self.policy.charge_mission_for(robot("amr-01", 10.0), sequence=7)

        self.assertEqual(request.mission_id, "charge-amr-01-0007")
        self.assertEqual(request.stop.station_id, "charger_01")
        self.assertIn("battery 10.0%", request.reason)


if __name__ == "__main__":
    unittest.main()
