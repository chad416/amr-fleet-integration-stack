"""Verification of exclusive, expiring station leases."""

import unittest

from amr_fleet_core import LeaseInvalid, NotFound, StationAccessManager, StationBusy


class StationAccessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manager = StationAccessManager({"infeed", "outfeed"}, default_lease_seconds=10.0)

    def test_station_access_is_exclusive(self) -> None:
        first = self.manager.acquire("infeed", "amr-01", "mission-1", now=100.0)

        with self.assertRaises(StationBusy):
            self.manager.acquire("infeed", "amr-02", "mission-2", now=101.0)

        validated = self.manager.validate(
            "infeed",
            first.lease_id,
            "amr-01",
            "mission-1",
            now=102.0,
        )
        self.assertEqual(validated, first)

    def test_repeated_request_is_idempotent(self) -> None:
        first = self.manager.acquire("infeed", "amr-01", "mission-1", now=100.0)
        repeated = self.manager.acquire("infeed", "amr-01", "mission-1", now=101.0)
        self.assertEqual(first.lease_id, repeated.lease_id)
        self.assertEqual(first.expires_at, repeated.expires_at)

    def test_expired_lease_cannot_authorize_docking(self) -> None:
        expired = self.manager.acquire("infeed", "amr-01", "mission-1", now=100.0)
        with self.assertRaises(LeaseInvalid):
            self.manager.validate(
                "infeed",
                expired.lease_id,
                "amr-01",
                "mission-1",
                now=110.0,
            )

        replacement = self.manager.acquire("infeed", "amr-02", "mission-2", now=110.0)
        self.assertNotEqual(expired.lease_id, replacement.lease_id)

    def test_mismatched_correlation_is_rejected(self) -> None:
        lease = self.manager.acquire("infeed", "amr-01", "mission-1", now=100.0)
        with self.assertRaises(LeaseInvalid):
            self.manager.validate("infeed", lease.lease_id, "amr-01", "mission-stale", now=101.0)

    def test_release_is_idempotent(self) -> None:
        lease = self.manager.acquire("infeed", "amr-01", "mission-1", now=100.0)
        self.assertTrue(self.manager.release("infeed", lease.lease_id, now=101.0))
        self.assertFalse(self.manager.release("infeed", lease.lease_id, now=102.0))

    def test_unknown_station_is_rejected(self) -> None:
        with self.assertRaises(NotFound):
            self.manager.acquire("unknown", "amr-01", "mission-1", now=100.0)


if __name__ == "__main__":
    unittest.main()
