"""Atomic multi-zone reservations for deadlock-free fleet route coordination."""

from __future__ import annotations

from dataclasses import dataclass

from .errors import TrafficConflict
from .traffic import TrafficManager, TrafficReservation


@dataclass(frozen=True, slots=True)
class RouteReservation:
    robot_id: str
    mission_id: str
    zones: tuple[TrafficReservation, ...]


class RouteCoordinator:
    """Reserve all constrained zones in a global order or reserve none of them."""

    def __init__(self, traffic: TrafficManager, *, zone_order: tuple[str, ...]) -> None:
        if not zone_order or len(set(zone_order)) != len(zone_order):
            raise ValueError("zone_order must contain unique zone IDs")
        self._traffic = traffic
        self._rank = {zone_id: index for index, zone_id in enumerate(zone_order)}

    def reserve_route(
        self,
        robot_id: str,
        mission_id: str,
        zone_ids: tuple[str, ...],
        *,
        now: float,
    ) -> RouteReservation:
        if len(set(zone_ids)) != len(zone_ids):
            raise ValueError("a route cannot contain duplicate traffic zones")
        try:
            ordered = tuple(sorted(zone_ids, key=self._rank.__getitem__))
        except KeyError as error:
            raise ValueError(
                f"route contains an unranked traffic zone: {error.args[0]}"
            ) from error

        acquired: list[TrafficReservation] = []
        try:
            for zone_id in ordered:
                acquired.append(
                    self._traffic.reserve(
                        zone_id,
                        robot_id,
                        mission_id,
                        now=now,
                    )
                )
        except TrafficConflict:
            for reservation in reversed(acquired):
                self._traffic.release(
                    reservation.zone_id,
                    robot_id,
                    mission_id,
                    now=now,
                )
            raise
        return RouteReservation(robot_id, mission_id, tuple(acquired))

    def release_route(self, reservation: RouteReservation, *, now: float) -> None:
        for zone in reversed(reservation.zones):
            self._traffic.release(
                zone.zone_id,
                reservation.robot_id,
                reservation.mission_id,
                now=now,
            )
