"""Verification of OPC UA and MQTT station transport codecs."""

import json
import unittest

from amr_fleet_core import StationLease
from amr_fleet_core.ot_transport import MqttStationCodec, OpcUaStationNodeSet


def lease() -> StationLease:
    return StationLease(
        lease_id="lease-1",
        station_id="station_infeed",
        robot_id="amr-01",
        mission_id="mission-1",
        granted_at=100.0,
        expires_at=130.0,
    )


class OtTransportTests(unittest.TestCase):
    def test_opcua_mapper_generates_correlated_entry_and_release_writes(self) -> None:
        nodes = OpcUaStationNodeSet(
            station_id="station_infeed",
            entry_request="ns=2;s=AMR.EntryRequest",
            entry_granted="ns=2;s=Station.EntryGranted",
            docked="ns=2;s=AMR.Docked",
            transfer_ready="ns=2;s=Station.TransferReady",
            transfer_complete="ns=2;s=Station.TransferComplete",
            release="ns=2;s=AMR.Release",
            lease_id="ns=2;s=AMR.LeaseId",
            heartbeat="ns=2;s=Station.Heartbeat",
            faulted="ns=2;s=Station.Faulted",
        )

        entry_writes = nodes.entry_request_writes(lease())
        release_writes = nodes.release_writes(lease())

        self.assertEqual(entry_writes[0].value, "lease-1")
        self.assertIn(("ns=2;s=AMR.EntryRequest", True), _as_pairs(entry_writes))
        self.assertIn(("ns=2;s=AMR.Release", True), _as_pairs(release_writes))

    def test_opcua_mapper_reads_plc_snapshot(self) -> None:
        nodes = OpcUaStationNodeSet(
            station_id="station_infeed",
            entry_request="request",
            entry_granted="granted",
            docked="docked",
            transfer_ready="ready",
            transfer_complete="complete",
            release="release",
            lease_id="lease",
            heartbeat="heartbeat",
            faulted="faulted",
        )

        snapshot = nodes.snapshot_from_values(
            {
                "granted": True,
                "ready": True,
                "complete": False,
                "faulted": False,
                "lease": "lease-1",
                "heartbeat": 101.0,
            },
            now=102.0,
        )

        self.assertTrue(snapshot.entry_granted)
        self.assertTrue(snapshot.transfer_ready)
        self.assertEqual(snapshot.lease_id, "lease-1")

    def test_mqtt_codec_generates_commands_and_decodes_status(self) -> None:
        codec = MqttStationCodec("station_infeed", base_topic="factory/amr")
        topic, payload = codec.entry_request_message(lease())
        body = json.loads(payload)

        self.assertEqual(topic, "factory/amr/station_infeed/command")
        self.assertEqual(body["command"], "entry_request")
        self.assertEqual(body["lease_id"], "lease-1")

        snapshot = codec.snapshot_from_message(
            "factory/amr/station_infeed/status",
            json.dumps(
                {
                    "station_id": "station_infeed",
                    "lease_id": "lease-1",
                    "entry_granted": True,
                    "transfer_ready": True,
                }
            ),
            received_at=111.0,
        )

        self.assertEqual(snapshot.heartbeat_at, 111.0)
        self.assertTrue(snapshot.entry_granted)
        self.assertTrue(snapshot.transfer_ready)


def _as_pairs(writes: tuple) -> set[tuple[str, object]]:
    return {(write.node_id, write.value) for write in writes}


if __name__ == "__main__":
    unittest.main()
