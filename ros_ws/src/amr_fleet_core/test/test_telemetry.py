"""Verification of telemetry projections and event sequencing."""

import unittest

from amr_fleet_core import (
    FleetService,
    InMemoryTelemetrySink,
    MissionStop,
    NearestEligibleDispatcher,
    Pose2D,
    RobotHealth,
    RobotSnapshot,
    StationAccessManager,
    project_fleet_telemetry,
)


class TelemetryTests(unittest.TestCase):
    def test_event_sink_assigns_monotonic_sequences(self) -> None:
        sink = InMemoryTelemetrySink()
        sink.record(timestamp=100.0, event_type="mission.submit", source="test")
        sink.record(timestamp=99.0, event_type="mission.dispatch", source="test")

        self.assertEqual([event.sequence for event in sink.events], [0, 1])

    def test_projector_flags_stale_robot_telemetry(self) -> None:
        service = FleetService(
            NearestEligibleDispatcher(
                minimum_battery=30.0,
                telemetry_stale_after=3.0,
            ),
            StationAccessManager({"infeed"}, default_lease_seconds=10.0),
        )
        service.update_robot(
            RobotSnapshot(
                robot_id="amr-stale",
                pose=Pose2D(0.0, 0.0),
                battery_percent=80.0,
                health=RobotHealth.HEALTHY,
                available=True,
                telemetry_at=100.0,
            )
        )
        service.submit_mission(
            "mission-telemetry",
            (MissionStop("infeed", "infeed_approach", Pose2D(1.0, 0.0)),),
        )

        snapshot = project_fleet_telemetry(
            service,
            now=104.1,
            telemetry_stale_after=3.0,
        )

        self.assertEqual(snapshot.stale_robot_ids, ("amr-stale",))
        self.assertTrue(snapshot.to_dict()["robots"][0]["stale"])
        self.assertEqual(snapshot.to_dict()["missions"][0]["state"], "queued")


if __name__ == "__main__":
    unittest.main()
