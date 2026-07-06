"""Verification of traffic-zone reservations for multi-robot coordination."""

import unittest

from amr_fleet_core import NotFound, TrafficConflict, TrafficManager


class TrafficManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manager = TrafficManager({"narrow_aisle", "dock_crossing"}, default_hold_seconds=5.0)

    def test_zone_reservation_is_exclusive_and_idempotent(self) -> None:
        first = self.manager.reserve("narrow_aisle", "amr-01", "mission-1", now=100.0)
        repeated = self.manager.reserve("narrow_aisle", "amr-01", "mission-1", now=101.0)

        self.assertEqual(first, repeated)
        with self.assertRaises(TrafficConflict):
            self.manager.reserve("narrow_aisle", "amr-02", "mission-2", now=102.0)

    def test_expired_reservation_can_be_replaced(self) -> None:
        self.manager.reserve("narrow_aisle", "amr-01", "mission-1", now=100.0)
        replacement = self.manager.reserve("narrow_aisle", "amr-02", "mission-2", now=105.0)

        self.assertEqual(replacement.robot_id, "amr-02")

    def test_release_requires_matching_owner(self) -> None:
        self.manager.reserve("dock_crossing", "amr-01", "mission-1", now=100.0)

        with self.assertRaises(TrafficConflict):
            self.manager.release("dock_crossing", "amr-02", "mission-2", now=101.0)
        self.assertTrue(self.manager.release("dock_crossing", "amr-01", "mission-1", now=102.0))
        self.assertFalse(self.manager.release("dock_crossing", "amr-01", "mission-1", now=103.0))

    def test_unknown_zone_is_rejected(self) -> None:
        with self.assertRaises(NotFound):
            self.manager.reserve("unknown", "amr-01", "mission-1", now=100.0)


if __name__ == "__main__":
    unittest.main()
