"""Verification of industrial station bridge reconciliation."""

import unittest

from amr_fleet_core import (
    LeaseInvalid,
    PlcStationSimulator,
    StationAccessManager,
    StationBridge,
    StationPlcSnapshot,
)


class StationBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.station_access = StationAccessManager({"infeed"}, default_lease_seconds=10.0)
        self.bridge = StationBridge(self.station_access, plc_stale_after=1.0)
        self.lease = self.bridge.request_entry(
            "infeed",
            "amr-01",
            "mission-1",
            now=100.0,
        )

    def test_valid_plc_grant_authorizes_docking_and_transfer(self) -> None:
        decision = self.bridge.reconcile(
            StationPlcSnapshot(
                station_id="infeed",
                heartbeat_at=100.5,
                entry_granted=True,
                transfer_ready=True,
                lease_id=self.lease.lease_id,
            ),
            lease_id=self.lease.lease_id,
            robot_id="amr-01",
            mission_id="mission-1",
            now=101.0,
        )

        self.assertTrue(decision.docking_authorized)
        self.assertTrue(decision.transfer_authorized)

    def test_stale_plc_snapshot_inhibits_docking(self) -> None:
        with self.assertRaises(LeaseInvalid):
            self.bridge.reconcile(
                StationPlcSnapshot(
                    station_id="infeed",
                    heartbeat_at=99.0,
                    entry_granted=True,
                    lease_id=self.lease.lease_id,
                ),
                lease_id=self.lease.lease_id,
                robot_id="amr-01",
                mission_id="mission-1",
                now=101.0,
            )

    def test_plc_lease_mismatch_is_rejected(self) -> None:
        with self.assertRaises(LeaseInvalid):
            self.bridge.reconcile(
                StationPlcSnapshot(
                    station_id="infeed",
                    heartbeat_at=101.0,
                    entry_granted=True,
                    lease_id="stale-lease",
                ),
                lease_id=self.lease.lease_id,
                robot_id="amr-01",
                mission_id="mission-1",
                now=101.0,
            )

    def test_plc_simulator_restart_clears_grant_and_inhibits_docking(self) -> None:
        plc = PlcStationSimulator("infeed")
        plc.receive_entry_request(self.lease, now=100.1)
        plc.grant_entry(now=100.2)
        plc.mark_transfer_ready(now=100.3)

        decision = self.bridge.reconcile(
            plc.snapshot(),
            lease_id=self.lease.lease_id,
            robot_id="amr-01",
            mission_id="mission-1",
            now=100.4,
        )
        self.assertTrue(decision.transfer_authorized)

        plc.restart(now=100.5)
        decision = self.bridge.reconcile(
            plc.snapshot(),
            lease_id=self.lease.lease_id,
            robot_id="amr-01",
            mission_id="mission-1",
            now=100.6,
        )
        self.assertFalse(decision.docking_authorized)
        self.assertFalse(decision.transfer_authorized)


if __name__ == "__main__":
    unittest.main()
