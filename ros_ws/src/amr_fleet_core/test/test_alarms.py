"""Verification of fleet alarm evaluation."""

import unittest

from amr_fleet_core import (
    FleetAlarmEvaluator,
    FleetService,
    MissionStop,
    NearestEligibleDispatcher,
    Pose2D,
    RobotHealth,
    RobotSnapshot,
    StationAccessManager,
    project_fleet_telemetry,
)


class FleetAlarmTests(unittest.TestCase):
    def test_alarms_cover_stale_robot_low_battery_failed_mission_and_lease_expiry(self) -> None:
        service = FleetService(
            NearestEligibleDispatcher(
                minimum_battery=5.0,
                telemetry_stale_after=3.0,
            ),
            StationAccessManager({"infeed"}, default_lease_seconds=10.0),
        )
        service.update_robot(
            RobotSnapshot(
                robot_id="amr-01",
                pose=Pose2D(0.0, 0.0),
                battery_percent=10.0,
                health=RobotHealth.HEALTHY,
                available=True,
                telemetry_at=100.0,
            )
        )
        service.submit_mission(
            "mission-fail",
            (MissionStop("infeed", "infeed_approach", Pose2D(1.0, 0.0)),),
        )
        service.dispatch("mission-fail", now=101.0)
        service.start("mission-fail")
        service.arrive_at_station_approach("mission-fail")
        service.request_station_access("mission-fail", now=102.0)
        service.fail("mission-fail", "test fault", now=103.0)
        snapshot = project_fleet_telemetry(
            service,
            now=104.0,
            telemetry_stale_after=3.0,
        )

        alarms = FleetAlarmEvaluator(critical_battery_percent=15.0).evaluate(snapshot)
        alarm_ids = {alarm.alarm_id for alarm in alarms}

        self.assertIn("robot:amr-01:telemetry_stale", alarm_ids)
        self.assertIn("robot:amr-01:battery_critical", alarm_ids)
        self.assertIn("mission:mission-fail:failed", alarm_ids)


if __name__ == "__main__":
    unittest.main()
