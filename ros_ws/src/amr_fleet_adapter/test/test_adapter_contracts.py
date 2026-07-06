"""Verification of pure ROS adapter contract helpers."""

import unittest

from amr_fleet_adapter.adapter_contracts import (
    MissionGoalRequest,
    mission_payload_from_goal,
    progress_percent,
    terminal_result_from_api_response,
    waypoint_catalog_from_json,
)

WAYPOINTS_JSON = """
[
  {
    "station_id": "station_infeed",
    "name": "infeed_dock",
    "approach_pose": {"x": 3.8, "y": 2.7, "yaw": 0.0, "frame_id": "map"}
  },
  {
    "station_id": "station_outfeed",
    "name": "outfeed_dock",
    "approach_pose": {"x": 3.8, "y": -2.7, "yaw": 0.0, "frame_id": "map"}
  }
]
"""


class AdapterContractTests(unittest.TestCase):
    def test_action_goal_maps_to_domain_mission_payload(self) -> None:
        catalog = waypoint_catalog_from_json(WAYPOINTS_JSON)
        payload = mission_payload_from_goal(
            MissionGoalRequest(
                mission_id="ros-mission-1",
                station_ids=("station_infeed", "station_outfeed"),
                waypoint_names=("infeed_dock", "outfeed_dock"),
            ),
            catalog,
        )

        self.assertEqual(payload["mission_id"], "ros-mission-1")
        self.assertEqual(payload["stops"][0]["station_id"], "station_infeed")
        self.assertEqual(payload["stops"][1]["approach_pose"]["y"], -2.7)

    def test_action_goal_requires_correlated_station_and_waypoint_lists(self) -> None:
        catalog = waypoint_catalog_from_json(WAYPOINTS_JSON)
        with self.assertRaises(ValueError):
            mission_payload_from_goal(
                MissionGoalRequest(
                    mission_id="bad",
                    station_ids=("station_infeed",),
                    waypoint_names=("infeed_dock", "outfeed_dock"),
                ),
                catalog,
            )

    def test_progress_and_terminal_result_are_protocol_safe(self) -> None:
        self.assertEqual(progress_percent("navigating", 1, 4), 25.0)
        self.assertEqual(progress_percent("completed", 1, 4), 100.0)
        result = terminal_result_from_api_response(
            {"mission": {"state": "failed", "failure_reason": "blocked"}}
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "MISSION_NOT_COMPLETED")


if __name__ == "__main__":
    unittest.main()
