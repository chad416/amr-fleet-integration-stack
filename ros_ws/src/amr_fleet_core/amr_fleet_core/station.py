"""Exclusive, expiring station-access leases."""

from __future__ import annotations

from dataclasses import dataclass
import uuid

from .errors import LeaseInvalid, NotFound, StationBusy


@dataclass(frozen=True, slots=True)
class StationLease:
    lease_id: str
    station_id: str
    robot_id: str
    mission_id: str
    granted_at: float
    expires_at: float

    def active_at(self, now: float) -> bool:
        return now < self.expires_at


class StationAccessManager:
    def __init__(self, station_ids: set[str], *, default_lease_seconds: float) -> None:
        if not station_ids:
            raise ValueError("at least one station must be configured")
        if any(not station_id.strip() for station_id in station_ids):
            raise ValueError("station IDs must be non-empty")
        if default_lease_seconds <= 0.0:
            raise ValueError("default_lease_seconds must be positive")
        self._station_ids = frozenset(station_ids)
        self._default_lease_seconds = default_lease_seconds
        self._leases: dict[str, StationLease] = {}

    def acquire(
        self,
        station_id: str,
        robot_id: str,
        mission_id: str,
        *,
        now: float,
    ) -> StationLease:
        self._require_station(station_id)
        current = self._leases.get(station_id)
        if current is not None and not current.active_at(now):
            del self._leases[station_id]
            current = None
        if current is not None:
            if current.robot_id == robot_id and current.mission_id == mission_id:
                return current
            raise StationBusy(f"station {station_id} is leased to {current.robot_id}")

        lease = StationLease(
            lease_id=str(uuid.uuid4()),
            station_id=station_id,
            robot_id=robot_id,
            mission_id=mission_id,
            granted_at=now,
            expires_at=now + self._default_lease_seconds,
        )
        self._leases[station_id] = lease
        return lease

    def validate(
        self,
        station_id: str,
        lease_id: str,
        robot_id: str,
        mission_id: str,
        *,
        now: float,
    ) -> StationLease:
        self._require_station(station_id)
        current = self._leases.get(station_id)
        if current is None or not current.active_at(now):
            self._leases.pop(station_id, None)
            raise LeaseInvalid(f"station {station_id} has no active lease")
        if (
            current.lease_id != lease_id
            or current.robot_id != robot_id
            or current.mission_id != mission_id
        ):
            raise LeaseInvalid("lease correlation fields do not match")
        return current

    def release(self, station_id: str, lease_id: str, *, now: float) -> bool:
        self._require_station(station_id)
        current = self._leases.get(station_id)
        if current is None:
            return False
        if not current.active_at(now):
            del self._leases[station_id]
            return False
        if current.lease_id != lease_id:
            raise LeaseInvalid("cannot release a different station lease")
        del self._leases[station_id]
        return True

    def active_leases(self, *, now: float) -> tuple[StationLease, ...]:
        expired = [
            station_id
            for station_id, lease in self._leases.items()
            if not lease.active_at(now)
        ]
        for station_id in expired:
            del self._leases[station_id]
        return tuple(sorted(self._leases.values(), key=lambda lease: lease.station_id))

    def _require_station(self, station_id: str) -> None:
        if station_id not in self._station_ids:
            raise NotFound(f"unknown station: {station_id}")
