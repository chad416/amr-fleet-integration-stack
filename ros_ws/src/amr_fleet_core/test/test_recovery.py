"""Verification of bounded autonomous mission recovery."""

import unittest

from amr_fleet_core import (
    FleetService,
    LeaseInvalid,
    MissionState,
    MissionStop,
    NearestEligibleDispatcher,
    Pose2D,
    RecoveryLimitExceeded,
    RobotHealth,
    RobotSnapshot,
    StationAccessManager,
)


class RecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.station_access = StationAccessManager({"infeed"}, default_lease_seconds=10.0)
        self.service = FleetService(
            NearestEligibleDispatcher(
                minimum_battery=30.0,
                telemetry_stale_after=3.0,
            ),
            self.station_access,
            recovery_max_attempts=2,
        )
        self.service.update_robot(
            RobotSnapshot(
                robot_id="amr-01",
                pose=Pose2D(0.0, 0.0),
                battery_percent=90.0,
                health=RobotHealth.HEALTHY,
                available=True,
                telemetry_at=100.0,
            )
        )
        self.stops = (MissionStop("infeed", "infeed_approach", Pose2D(1.0, 0.0)),)

    def test_recovery_returns_to_navigation_until_budget_is_exhausted(self) -> None:
        mission = self.service.submit_mission("recover-1", self.stops)
        self.service.dispatch("recover-1", now=101.0)
        self.service.start("recover-1")

        self.assertEqual(self.service.begin_recovery("recover-1", "blocked path", now=102.0), 1)
        self.assertEqual(mission.state, MissionState.RECOVERING)
        self.service.complete_recovery("recover-1")
        self.assertEqual(mission.state, MissionState.NAVIGATING)

        self.assertEqual(
            self.service.begin_recovery("recover-1", "controller timeout", now=103.0),
            2,
        )
        self.service.complete_recovery("recover-1")

        with self.assertRaises(RecoveryLimitExceeded):
            self.service.begin_recovery("recover-1", "planner still blocked", now=104.0)
        self.assertEqual(mission.state, MissionState.FAILED)
        self.assertEqual(self.service.active_mission_by_robot(), {})

    def test_recovery_from_approach_releases_station_lease(self) -> None:
        self.service.submit_mission("recover-lease", self.stops)
        self.service.dispatch("recover-lease", now=101.0)
        self.service.start("recover-lease")
        self.service.arrive_at_station_approach("recover-lease")
        lease = self.service.request_station_access("recover-lease", now=102.0)

        self.service.begin_recovery("recover-lease", "station grant dropped", now=103.0)

        with self.assertRaises(LeaseInvalid):
            self.station_access.validate(
                "infeed",
                lease.lease_id,
                "amr-01",
                "recover-lease",
                now=104.0,
            )


if __name__ == "__main__":
    unittest.main()
