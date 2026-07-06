"""Named waypoint and station approach catalog."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .errors import NotFound
from .models import MissionStop, Pose2D


@dataclass(frozen=True, slots=True)
class Waypoint:
    name: str
    station_id: str
    approach_pose: Pose2D

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("waypoint name must be non-empty")
        if not self.station_id.strip():
            raise ValueError("station_id must be non-empty")


class WaypointCatalog:
    """Immutable lookup table from named station waypoints to mission stops."""

    def __init__(self, waypoints: tuple[Waypoint, ...]) -> None:
        if not waypoints:
            raise ValueError("at least one waypoint is required")
        self._by_station_and_name: dict[tuple[str, str], Waypoint] = {}
        for waypoint in waypoints:
            key = (waypoint.station_id, waypoint.name)
            if key in self._by_station_and_name:
                raise ValueError(f"duplicate waypoint for station/name: {key}")
            self._by_station_and_name[key] = waypoint

    @classmethod
    def from_records(cls, records: list[dict[str, Any]]) -> WaypointCatalog:
        return cls(tuple(_waypoint_from_record(record) for record in records))

    def resolve(self, station_id: str, waypoint_name: str) -> MissionStop:
        key = (station_id, waypoint_name)
        try:
            waypoint = self._by_station_and_name[key]
        except KeyError as error:
            raise NotFound(f"unknown waypoint {waypoint_name} for station {station_id}") from error
        return MissionStop(
            station_id=station_id,
            waypoint=waypoint.name,
            approach_pose=waypoint.approach_pose,
        )

    def station_ids(self) -> set[str]:
        return {station_id for station_id, _ in self._by_station_and_name}


def _waypoint_from_record(record: dict[str, Any]) -> Waypoint:
    pose = record.get("approach_pose")
    if not isinstance(pose, dict):
        raise ValueError("waypoint record requires approach_pose object")
    return Waypoint(
        name=_require_string(record, "name"),
        station_id=_require_string(record, "station_id"),
        approach_pose=Pose2D(
            x=float(pose["x"]),
            y=float(pose["y"]),
            yaw=float(pose.get("yaw", 0.0)),
            frame_id=str(pose.get("frame_id", "map")),
        ),
    )


def _require_string(record: dict[str, Any], field: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value
