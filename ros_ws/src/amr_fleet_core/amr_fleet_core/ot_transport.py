"""Transport codecs for station OPC UA and MQTT integration boundaries."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .ot import StationPlcSnapshot
from .station import StationLease


@dataclass(frozen=True, slots=True)
class OpcUaWrite:
    node_id: str
    value: bool | str | float


@dataclass(frozen=True, slots=True)
class OpcUaStationNodeSet:
    station_id: str
    entry_request: str
    entry_granted: str
    docked: str
    transfer_ready: str
    transfer_complete: str
    release: str
    lease_id: str
    heartbeat: str
    faulted: str

    def __post_init__(self) -> None:
        fields = (
            self.station_id,
            self.entry_request,
            self.entry_granted,
            self.docked,
            self.transfer_ready,
            self.transfer_complete,
            self.release,
            self.lease_id,
            self.heartbeat,
            self.faulted,
        )
        if any(not field.strip() for field in fields):
            raise ValueError("OPC UA station node fields must be non-empty")

    def entry_request_writes(self, lease: StationLease) -> tuple[OpcUaWrite, ...]:
        self._require_matching_station(lease.station_id)
        return (
            OpcUaWrite(self.lease_id, lease.lease_id),
            OpcUaWrite(self.entry_request, True),
            OpcUaWrite(self.release, False),
        )

    def release_writes(self, lease: StationLease) -> tuple[OpcUaWrite, ...]:
        self._require_matching_station(lease.station_id)
        return (
            OpcUaWrite(self.lease_id, lease.lease_id),
            OpcUaWrite(self.entry_request, False),
            OpcUaWrite(self.release, True),
        )

    def snapshot_from_values(
        self,
        values: dict[str, Any],
        *,
        now: float,
    ) -> StationPlcSnapshot:
        return StationPlcSnapshot(
            station_id=self.station_id,
            heartbeat_at=float(values.get(self.heartbeat, now)),
            entry_granted=bool(values.get(self.entry_granted, False)),
            transfer_ready=bool(values.get(self.transfer_ready, False)),
            transfer_complete=bool(values.get(self.transfer_complete, False)),
            faulted=bool(values.get(self.faulted, False)),
            lease_id=_optional_string(values.get(self.lease_id)),
        )

    def _require_matching_station(self, station_id: str) -> None:
        if station_id != self.station_id:
            raise ValueError(f"lease station {station_id} does not match {self.station_id}")


@dataclass(frozen=True, slots=True)
class MqttStationCodec:
    station_id: str
    base_topic: str = "amr/stations"

    def __post_init__(self) -> None:
        if not self.station_id.strip():
            raise ValueError("station_id must be non-empty")
        if not self.base_topic.strip():
            raise ValueError("base_topic must be non-empty")

    @property
    def command_topic(self) -> str:
        return f"{self.base_topic}/{self.station_id}/command"

    @property
    def status_topic(self) -> str:
        return f"{self.base_topic}/{self.station_id}/status"

    def entry_request_message(self, lease: StationLease) -> tuple[str, str]:
        self._require_matching_station(lease.station_id)
        return (
            self.command_topic,
            json.dumps(
                {
                    "command": "entry_request",
                    "station_id": lease.station_id,
                    "robot_id": lease.robot_id,
                    "mission_id": lease.mission_id,
                    "lease_id": lease.lease_id,
                    "expires_at": lease.expires_at,
                },
                sort_keys=True,
            ),
        )

    def release_message(self, lease: StationLease) -> tuple[str, str]:
        self._require_matching_station(lease.station_id)
        return (
            self.command_topic,
            json.dumps(
                {
                    "command": "release",
                    "station_id": lease.station_id,
                    "robot_id": lease.robot_id,
                    "mission_id": lease.mission_id,
                    "lease_id": lease.lease_id,
                },
                sort_keys=True,
            ),
        )

    def snapshot_from_message(
        self,
        topic: str,
        payload: str,
        *,
        received_at: float,
    ) -> StationPlcSnapshot:
        if topic != self.status_topic:
            raise ValueError(f"unexpected station status topic: {topic}")
        body = json.loads(payload)
        if not isinstance(body, dict):
            raise ValueError("station status payload must be an object")
        station_id = str(body.get("station_id", self.station_id))
        if station_id != self.station_id:
            raise ValueError(f"station status belongs to {station_id}, not {self.station_id}")
        return StationPlcSnapshot(
            station_id=self.station_id,
            heartbeat_at=float(body.get("heartbeat_at", received_at)),
            entry_granted=bool(body.get("entry_granted", False)),
            transfer_ready=bool(body.get("transfer_ready", False)),
            transfer_complete=bool(body.get("transfer_complete", False)),
            faulted=bool(body.get("faulted", False)),
            lease_id=_optional_string(body.get("lease_id")),
        )

    def _require_matching_station(self, station_id: str) -> None:
        if station_id != self.station_id:
            raise ValueError(f"lease station {station_id} does not match {self.station_id}")


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None
