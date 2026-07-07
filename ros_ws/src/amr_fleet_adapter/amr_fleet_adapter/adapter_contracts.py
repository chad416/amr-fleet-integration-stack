"""Pure adapter contract helpers shared by ROS nodes and tests."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from amr_fleet_core import WaypointCatalog


@dataclass(frozen=True, slots=True)
class MissionGoalRequest:
    mission_id: str
    station_ids: tuple[str, ...]
    waypoint_names: tuple[str, ...]


def waypoint_catalog_from_json(payload: str) -> WaypointCatalog:
    records = json.loads(payload)
    if not isinstance(records, list):
        raise ValueError("waypoint_records_json must decode to a list")
    return WaypointCatalog.from_records(records)


def mission_payload_from_goal(
    goal: MissionGoalRequest,
    catalog: WaypointCatalog,
) -> dict[str, Any]:
    if not goal.mission_id.strip():
        raise ValueError("mission_id must be non-empty")
    if len(goal.station_ids) != len(goal.waypoint_names):
        raise ValueError("station_ids and waypoint_names must have the same length")
    if not goal.station_ids:
        raise ValueError("mission goal requires at least one stop")

    stops: list[dict[str, Any]] = []
    for station_id, waypoint_name in zip(goal.station_ids, goal.waypoint_names, strict=True):
        stop = catalog.resolve(station_id, waypoint_name)
        pose = stop.approach_pose
        stops.append(
            {
                "station_id": stop.station_id,
                "waypoint": stop.waypoint,
                "approach_pose": {
                    "x": pose.x,
                    "y": pose.y,
                    "yaw": pose.yaw,
                    "frame_id": pose.frame_id,
                },
            }
        )
    return {"mission_id": goal.mission_id, "stops": stops}


def progress_percent(state: str, current_stop_index: int, stop_count: int) -> float:
    if state in {"completed", "canceled", "failed"}:
        return 100.0
    if stop_count <= 0:
        return 0.0
    return min(99.0, max(0.0, (current_stop_index / stop_count) * 100.0))


def terminal_result_from_api_response(response_body: dict[str, Any]) -> dict[str, Any]:
    mission = response_body.get("mission", {})
    state = str(mission.get("state", "unknown"))
    return {
        "success": state == "completed",
        "terminal_state": state,
        "error_code": "" if state == "completed" else "MISSION_NOT_COMPLETED",
        "detail": str(mission.get("failure_reason") or state),
    }
