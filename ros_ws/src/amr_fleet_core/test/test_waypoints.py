"""Verification of named waypoint catalog resolution."""

import unittest

from amr_fleet_core import NotFound, Pose2D, Waypoint, WaypointCatalog, create_fleet_api


class WaypointCatalogTests(unittest.TestCase):
    def test_catalog_resolves_station_waypoint_to_mission_stop(self) -> None:
        catalog = WaypointCatalog(
            (
                Waypoint(
                    name="infeed_approach",
                    station_id="infeed",
                    approach_pose=Pose2D(1.25, -0.5, 1.57),
                ),
            )
        )

        stop = catalog.resolve("infeed", "infeed_approach")

        self.assertEqual(stop.station_id, "infeed")
        self.assertEqual(stop.waypoint, "infeed_approach")
        self.assertEqual(stop.approach_pose.x, 1.25)

    def test_unknown_named_waypoint_is_rejected(self) -> None:
        catalog = WaypointCatalog(
            (
                Waypoint(
                    name="infeed_approach",
                    station_id="infeed",
                    approach_pose=Pose2D(1.0, 0.0),
                ),
            )
        )

        with self.assertRaises(NotFound):
            catalog.resolve("infeed", "missing")

    def test_api_accepts_named_stop_when_catalog_is_configured(self) -> None:
        catalog = WaypointCatalog(
            (
                Waypoint(
                    name="infeed_approach",
                    station_id="infeed",
                    approach_pose=Pose2D(1.0, 0.0),
                ),
            )
        )
        api = create_fleet_api(
            station_ids={"infeed"},
            telemetry_stale_after=3.0,
            waypoint_catalog=catalog,
        )

        response = api.submit_mission(
            {
                "mission_id": "named-waypoint",
                "stops": [{"station_id": "infeed", "waypoint": "infeed_approach"}],
            }
        )

        self.assertTrue(response.ok)
        self.assertEqual(response.body["mission"]["current_stop"]["approach_pose"]["x"], 1.0)


if __name__ == "__main__":
    unittest.main()
