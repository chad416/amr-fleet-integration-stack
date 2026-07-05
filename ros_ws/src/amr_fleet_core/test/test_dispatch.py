"""Verification of deterministic dispatch eligibility and ranking."""

import unittest

from amr_fleet_core import (
    MissionStop,
    NearestEligibleDispatcher,
    NoEligibleRobot,
    Pose2D,
    RobotHealth,
    RobotSnapshot,
)


def robot(
    robot_id: str,
    x: float,
    *,
    battery: float = 80.0,
    health: RobotHealth = RobotHealth.HEALTHY,
    available: bool = True,
    telemetry_at: float = 100.0,
) -> RobotSnapshot:
    return RobotSnapshot(
        robot_id=robot_id,
        pose=Pose2D(x, 0.0),
        battery_percent=battery,
        health=health,
        available=available,
        telemetry_at=telemetry_at,
    )


class DispatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dispatcher = NearestEligibleDispatcher(
            minimum_battery=30.0,
            telemetry_stale_after=3.0,
            reject_degraded=True,
        )
        self.target = MissionStop("infeed", "infeed_approach", Pose2D(10.0, 0.0))

    def test_selects_nearest_eligible_robot(self) -> None:
        selected = self.dispatcher.select(
            [robot("amr-01", 0.0), robot("amr-02", 9.0)],
            self.target,
            now=101.0,
        )
        self.assertEqual(selected.robot_id, "amr-02")

    def test_tie_breaker_is_robot_id(self) -> None:
        selected = self.dispatcher.select(
            [robot("amr-02", 9.0), robot("amr-01", 11.0)],
            self.target,
            now=101.0,
        )
        self.assertEqual(selected.robot_id, "amr-01")

    def test_rejects_all_ineligible_categories(self) -> None:
        fleet = [
            robot("low-battery", 9.0, battery=29.9),
            robot("stale", 9.0, telemetry_at=97.9),
            robot("degraded", 9.0, health=RobotHealth.DEGRADED),
            robot("fault", 9.0, health=RobotHealth.FAULT),
            robot("unavailable", 9.0, available=False),
            robot("busy", 9.0),
        ]
        with self.assertRaises(NoEligibleRobot):
            self.dispatcher.select(
                fleet,
                self.target,
                now=101.0,
                busy_robot_ids={"busy"},
            )

    def test_future_clock_skew_does_not_make_telemetry_stale(self) -> None:
        selected = self.dispatcher.select(
            [robot("amr-01", 9.0, telemetry_at=101.5)],
            self.target,
            now=101.0,
        )
        self.assertEqual(selected.robot_id, "amr-01")


if __name__ == "__main__":
    unittest.main()
