"""Verification of multi-robot dispatch coordination."""

import unittest

from amr_fleet_core import (
    FleetService,
    MissionStop,
    NearestEligibleDispatcher,
    Pose2D,
    RobotHealth,
    RobotSnapshot,
    StationAccessManager,
    create_fleet_api,
)


def robot(robot_id: str, x: float, telemetry_at: float = 100.0) -> RobotSnapshot:
    return RobotSnapshot(
        robot_id=robot_id,
        pose=Pose2D(x, 0.0),
        battery_percent=90.0,
        health=RobotHealth.HEALTHY,
        available=True,
        telemetry_at=telemetry_at,
    )


class MultiRobotDispatchTests(unittest.TestCase):
    def test_batch_dispatch_skips_busy_robots_and_assigns_remaining_fleet(self) -> None:
        service = FleetService(
            NearestEligibleDispatcher(
                minimum_battery=30.0,
                telemetry_stale_after=3.0,
            ),
            StationAccessManager({"infeed", "outfeed"}, default_lease_seconds=10.0),
        )
        service.update_robot(robot("amr-01", 0.0))
        service.update_robot(robot("amr-02", 10.0))
        service.submit_mission(
            "mission-a",
            (MissionStop("infeed", "infeed_approach", Pose2D(1.0, 0.0)),),
        )
        service.submit_mission(
            "mission-b",
            (MissionStop("outfeed", "outfeed_approach", Pose2D(9.0, 0.0)),),
        )

        assignments = service.dispatch_all(now=101.0)

        self.assertEqual(assignments, (("mission-a", "amr-01"), ("mission-b", "amr-02")))
        self.assertEqual(
            service.active_mission_by_robot(),
            {"amr-01": "mission-a", "amr-02": "mission-b"},
        )

    def test_http_api_batch_dispatch_returns_assignments(self) -> None:
        api = create_fleet_api(
            station_ids={"infeed", "outfeed"},
            telemetry_stale_after=3.0,
        )
        self.assertTrue(
            api.update_robot(
                {
                    "robot_id": "amr-01",
                    "pose": {"x": 0.0, "y": 0.0},
                    "battery_percent": 90.0,
                    "health": "healthy",
                    "available": True,
                    "telemetry_at": 100.0,
                }
            ).ok
        )
        self.assertTrue(
            api.update_robot(
                {
                    "robot_id": "amr-02",
                    "pose": {"x": 10.0, "y": 0.0},
                    "battery_percent": 90.0,
                    "health": "healthy",
                    "available": True,
                    "telemetry_at": 100.0,
                }
            ).ok
        )
        for mission_id, station_id, x in (
            ("mission-api-a", "infeed", 1.0),
            ("mission-api-b", "outfeed", 9.0),
        ):
            self.assertTrue(
                api.submit_mission(
                    {
                        "mission_id": mission_id,
                        "stops": [
                            {
                                "station_id": station_id,
                                "waypoint": f"{station_id}_approach",
                                "approach_pose": {"x": x, "y": 0.0},
                            }
                        ],
                    }
                ).ok
            )

        response = api.dispatch_all({"now": 101.0})

        self.assertTrue(response.ok)
        self.assertEqual(
            response.body["assignments"],
            [
                {"mission_id": "mission-api-a", "robot_id": "amr-01"},
                {"mission_id": "mission-api-b", "robot_id": "amr-02"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
