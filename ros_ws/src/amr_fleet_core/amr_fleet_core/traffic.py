"""Traffic-zone reservation primitives for multi-robot coordination."""

from __future__ import annotations

from dataclasses import dataclass

from .errors import NotFound, TrafficConflict


@dataclass(frozen=True, slots=True)
class TrafficReservation:
    zone_id: str
    robot_id: str
    mission_id: str
    granted_at: float
    expires_at: float

    def active_at(self, now: float) -> bool:
        return now < self.expires_at


class TrafficManager:
    """Exclusive expiring reservations for narrow aisles, doors and crossings."""

    def __init__(self, zone_ids: set[str], *, default_hold_seconds: float) -> None:
        if not zone_ids:
            raise ValueError("at least one traffic zone must be configured")
        if any(not zone_id.strip() for zone_id in zone_ids):
            raise ValueError("traffic zone IDs must be non-empty")
        if default_hold_seconds <= 0.0:
            raise ValueError("default_hold_seconds must be positive")
        self._zone_ids = frozenset(zone_ids)
        self._default_hold_seconds = default_hold_seconds
        self._reservations: dict[str, TrafficReservation] = {}

    def reserve(
        self,
        zone_id: str,
        robot_id: str,
        mission_id: str,
        *,
        now: float,
    ) -> TrafficReservation:
        self._require_zone(zone_id)
        if not robot_id.strip():
            raise ValueError("robot_id must be non-empty")
        if not mission_id.strip():
            raise ValueError("mission_id must be non-empty")

        current = self._reservations.get(zone_id)
        if current is not None and not current.active_at(now):
            del self._reservations[zone_id]
            current = None
        if current is not None:
            if current.robot_id == robot_id and current.mission_id == mission_id:
                return current
            raise TrafficConflict(f"zone {zone_id} is reserved by {current.robot_id}")

        reservation = TrafficReservation(
            zone_id=zone_id,
            robot_id=robot_id,
            mission_id=mission_id,
            granted_at=now,
            expires_at=now + self._default_hold_seconds,
        )
        self._reservations[zone_id] = reservation
        return reservation

    def release(self, zone_id: str, robot_id: str, mission_id: str, *, now: float) -> bool:
        self._require_zone(zone_id)
        current = self._reservations.get(zone_id)
        if current is None:
            return False
        if not current.active_at(now):
            del self._reservations[zone_id]
            return False
        if current.robot_id != robot_id or current.mission_id != mission_id:
            raise TrafficConflict("cannot release a reservation owned by another robot")
        del self._reservations[zone_id]
        return True

    def active_reservations(self, *, now: float) -> tuple[TrafficReservation, ...]:
        expired = [
            zone_id
            for zone_id, reservation in self._reservations.items()
            if not reservation.active_at(now)
        ]
        for zone_id in expired:
            del self._reservations[zone_id]
        return tuple(sorted(self._reservations.values(), key=lambda item: item.zone_id))

    def _require_zone(self, zone_id: str) -> None:
        if zone_id not in self._zone_ids:
            raise NotFound(f"unknown traffic zone: {zone_id}")
