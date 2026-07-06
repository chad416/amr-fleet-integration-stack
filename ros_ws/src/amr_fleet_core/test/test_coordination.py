"""Verification of atomic deadlock-free traffic route reservations."""

import unittest

from amr_fleet_core import TrafficConflict, TrafficManager
from amr_fleet_core.coordination import RouteCoordinator


class RouteCoordinatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.traffic = TrafficManager(
            {"aisle_a", "crossing", "aisle_b"},
            default_hold_seconds=30.0,
        )
        self.coordinator = RouteCoordinator(
            self.traffic,
            zone_order=("aisle_a", "crossing", "aisle_b"),
        )

    def test_route_is_reserved_in_global_order_and_released(self) -> None:
        reservation = self.coordinator.reserve_route(
            "amr-01",
            "mission-01",
            ("aisle_b", "crossing"),
            now=10.0,
        )
        self.assertEqual(
            ("crossing", "aisle_b"),
            tuple(zone.zone_id for zone in reservation.zones),
        )
        self.coordinator.release_route(reservation, now=11.0)
        self.assertEqual((), self.traffic.active_reservations(now=11.0))

    def test_conflict_rolls_back_partial_reservation_atomically(self) -> None:
        self.traffic.reserve("aisle_b", "amr-02", "mission-02", now=10.0)
        with self.assertRaises(TrafficConflict):
            self.coordinator.reserve_route(
                "amr-01",
                "mission-01",
                ("aisle_a", "aisle_b"),
                now=10.0,
            )
        active = self.traffic.active_reservations(now=10.0)
        self.assertEqual(("aisle_b",), tuple(item.zone_id for item in active))


if __name__ == "__main__":
    unittest.main()
