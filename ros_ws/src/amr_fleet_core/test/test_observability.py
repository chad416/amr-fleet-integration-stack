"""Verification of metrics export for dashboards and historians."""

import unittest

from amr_fleet_core import (
    FleetService,
    InMemoryTelemetrySink,
    InfluxLineProtocolExporter,
    MissionStop,
    NearestEligibleDispatcher,
    Pose2D,
    RobotHealth,
    RobotSnapshot,
    StationAccessManager,
    project_fleet_telemetry,
)


class ObservabilityTests(unittest.TestCase):
    def test_influx_exporter_renders_robot_mission_and_events(self) -> None:
        service = FleetService(
            NearestEligibleDispatcher(
                minimum_battery=30.0,
                telemetry_stale_after=3.0,
            ),
            StationAccessManager({"infeed"}, default_lease_seconds=10.0),
        )
        service.update_robot(
            RobotSnapshot(
                robot_id="amr 01",
                pose=Pose2D(0.0, 0.0),
                battery_percent=77.5,
                health=RobotHealth.HEALTHY,
                available=True,
                telemetry_at=100.0,
            )
        )
        service.submit_mission(
            "mission,one",
            (MissionStop("infeed", "infeed_approach", Pose2D(1.0, 0.0)),),
        )
        snapshot = project_fleet_telemetry(
            service,
            now=101.0,
            telemetry_stale_after=3.0,
        )
        sink = InMemoryTelemetrySink()
        sink.record(
            timestamp=101.0,
            event_type="mission.submit",
            source="test",
            payload={"mission_id": "mission,one"},
        )

        exporter = InfluxLineProtocolExporter()
        metrics = exporter.export_snapshot(snapshot)
        events = exporter.export_events(sink.events)

        self.assertIn("amr_robot,robot_id=amr\\ 01", metrics)
        self.assertIn("battery_percent=77.5", metrics)
        self.assertIn("mission_id=mission\\,one", metrics)
        self.assertIn("amr_event,event_type=mission.submit", events)
        self.assertIn("sequence=0i", events)


if __name__ == "__main__":
    unittest.main()
