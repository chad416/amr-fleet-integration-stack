"""End-to-end verification of fleet application-service invariants."""

import unittest

from amr_fleet_core import (
    DuplicateMissionConflict,
    FleetService,
    LeaseInvalid,
    MissionState,
    MissionStop,
    NearestEligibleDispatcher,
    Pose2D,
    RobotHealth,
    RobotSnapshot,
    StationAccessManager,
)


class FleetServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = FleetService(
            NearestEligibleDispatcher(
                minimum_battery=30.0,
                telemetry_stale_after=3.0,
            ),
            StationAccessManager({"infeed", "outfeed"}, default_lease_seconds=10.0),
        )
        self.service.update_robot(
            RobotSnapshot(
                robot_id="amr-01",
                pose=Pose2D(0.0, 0.0),
                battery_percent=80.0,
                health=RobotHealth.HEALTHY,
                available=True,
                telemetry_at=100.0,
            )
        )
        self.stops = (MissionStop("infeed", "infeed_approach", Pose2D(1.0, 0.0)),)

    def test_end_to_end_station_mission(self) -> None:
        mission = self.service.submit_mission("mission-1", self.stops)
        self.assertEqual(self.service.dispatch("mission-1", now=101.0), "amr-01")
        self.service.start("mission-1")
        self.service.arrive_at_station_approach("mission-1")
        lease = self.service.request_station_access("mission-1", now=102.0)
        self.service.start_docking("mission-1", lease.lease_id, now=103.0)
        self.service.confirm_docked("mission-1", lease.lease_id, now=104.0)
        self.service.complete_transfer("mission-1", lease.lease_id, now=105.0)

        self.assertEqual(mission.state, MissionState.COMPLETED)

    def test_expired_lease_blocks_docking(self) -> None:
        self.service.submit_mission("mission-1", self.stops)
        self.service.dispatch("mission-1", now=101.0)
        self.service.start("mission-1")
        self.service.arrive_at_station_approach("mission-1")
        lease = self.service.request_station_access("mission-1", now=102.0)

        with self.assertRaises(LeaseInvalid):
            self.service.start_docking("mission-1", lease.lease_id, now=112.0)

    def test_operator_pause_and_resume(self) -> None:
        mission = self.service.submit_mission("mission-1", self.stops)
        self.service.dispatch("mission-1", now=101.0)
        self.service.start("mission-1")

        self.service.pause("mission-1")
        self.assertEqual(mission.state, MissionState.PAUSED)
        self.service.resume("mission-1")
        self.assertEqual(mission.state, MissionState.NAVIGATING)

    def test_mission_submission_is_idempotent_but_payload_is_immutable(self) -> None:
        first = self.service.submit_mission("mission-1", self.stops)
        repeated = self.service.submit_mission("mission-1", self.stops)
        self.assertIs(first, repeated)

        changed = (MissionStop("outfeed", "outfeed_approach", Pose2D(2.0, 0.0)),)
        with self.assertRaises(DuplicateMissionConflict):
            self.service.submit_mission("mission-1", changed)

    def test_older_telemetry_does_not_replace_newer_snapshot(self) -> None:
        self.service.update_robot(
            RobotSnapshot(
                robot_id="amr-01",
                pose=Pose2D(100.0, 0.0),
                battery_percent=1.0,
                health=RobotHealth.FAULT,
                available=False,
                telemetry_at=99.0,
            )
        )
        self.service.submit_mission("mission-1", self.stops)
        self.assertEqual(self.service.dispatch("mission-1", now=101.0), "amr-01")


if __name__ == "__main__":
    unittest.main()
