"""Verification of the remote mission API facade."""

import statistics
import time
import unittest

from amr_fleet_core import MissionState, create_fleet_api


def robot_payload(now: float = 100.0) -> dict:
    return {
        "robot_id": "amr-01",
        "pose": {"x": 0.0, "y": 0.0, "yaw": 0.0, "frame_id": "map"},
        "battery_percent": 82.0,
        "health": "healthy",
        "available": True,
        "telemetry_at": now,
    }


def mission_payload(mission_id: str = "mission-api-001") -> dict:
    return {
        "mission_id": mission_id,
        "stops": [
            {
                "station_id": "infeed",
                "waypoint": "infeed_approach",
                "approach_pose": {"x": 1.0, "y": 0.0, "yaw": 0.0},
            }
        ],
    }


class FleetApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = 100.0
        self.api = create_fleet_api(
            station_ids={"infeed"},
            station_lease_seconds=10.0,
            telemetry_stale_after=3.0,
            recovery_max_attempts=2,
            clock=lambda: self.now,
        )
        self.assertTrue(self.api.update_robot(robot_payload(self.now)).ok)

    def test_remote_lifecycle_completes_station_mission(self) -> None:
        self.assertEqual(self.api.submit_mission(mission_payload()).status, 201)
        self.assertTrue(self.api.dispatch("mission-api-001", {"now": 101.0}).ok)
        self.assertTrue(self.api.start("mission-api-001").ok)
        self.assertTrue(self.api.arrive_at_station_approach("mission-api-001").ok)
        lease = self.api.request_station_access("mission-api-001", {"now": 102.0})
        self.assertTrue(lease.ok)
        lease_id = lease.body["lease"]["lease_id"]

        self.assertTrue(
            self.api.start_docking(
                "mission-api-001",
                {"lease_id": lease_id, "now": 103.0},
            ).ok
        )
        self.assertTrue(
            self.api.confirm_docked(
                "mission-api-001",
                {"lease_id": lease_id, "now": 104.0},
            ).ok
        )
        done = self.api.complete_transfer("mission-api-001", {"lease_id": lease_id, "now": 105.0})

        self.assertEqual(done.body["mission"]["state"], MissionState.COMPLETED.value)
        telemetry = self.api.telemetry(now=105.0)
        self.assertEqual(telemetry.body["fleet"]["missions"][0]["state"], "completed")
        self.assertEqual(
            [event["sequence"] for event in telemetry.body["events"]],
            list(range(len(telemetry.body["events"]))),
        )

    def test_api_translates_domain_errors_without_throwing(self) -> None:
        response = self.api.dispatch("unknown", {"now": 101.0})

        self.assertFalse(response.ok)
        self.assertEqual(response.status, 404)
        self.assertEqual(response.body["error"]["code"], "NotFound")

    def test_idempotent_submission_keeps_original_payload(self) -> None:
        first = self.api.submit_mission(mission_payload("mission-repeat"))
        repeated = self.api.submit_mission(mission_payload("mission-repeat"))
        changed = mission_payload("mission-repeat")
        changed["stops"][0]["station_id"] = "other"

        self.assertTrue(first.ok)
        self.assertTrue(repeated.ok)
        self.assertFalse(self.api.submit_mission(changed).ok)

    def test_command_acknowledgement_p95_is_below_500_ms(self) -> None:
        durations = []
        for index in range(100):
            payload = mission_payload(f"ack-{index:03d}")
            start = time.perf_counter()
            response = self.api.submit_mission(payload)
            durations.append((time.perf_counter() - start) * 1000.0)
            self.assertTrue(response.ok)

        p95 = statistics.quantiles(durations, n=100)[94]
        self.assertLess(p95, 500.0)


if __name__ == "__main__":
    unittest.main()
