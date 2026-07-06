"""Executable MQTT station automation around the transport-independent fleet core."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

from .api import FleetApi
from .errors import LeaseInvalid, NotFound
from .models import MissionState
from .ot import StationBridge, StationBridgeDecision
from .ot_transport import MqttStationCodec
from .station import StationLease


class MessagePublisher(Protocol):
    def publish(
        self,
        topic: str,
        payload: str,
        *,
        qos: int = 1,
        retain: bool = False,
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class StationAutomationResult:
    station_id: str
    mission_id: str
    state: MissionState
    decision: StationBridgeDecision
    within_docking_tolerance: bool


class MqttStationCoordinator:
    """Correlate fleet leases with MQTT PLC status and advance pseudo-docking."""

    def __init__(
        self,
        api: FleetApi,
        publisher: MessagePublisher,
        station_ids: tuple[str, ...],
        *,
        plc_stale_after: float = 3.0,
        docking_position_tolerance: float = 0.20,
    ) -> None:
        if not station_ids or len(set(station_ids)) != len(station_ids):
            raise ValueError("station_ids must be non-empty and unique")
        if docking_position_tolerance <= 0.0:
            raise ValueError("docking_position_tolerance must be positive")
        self._api = api
        self._publisher = publisher
        self._codecs = {
            station_id: MqttStationCodec(station_id) for station_id in station_ids
        }
        self._bridges = {
            station_id: StationBridge(
                api.service.station_access,
                plc_stale_after=plc_stale_after,
            )
            for station_id in station_ids
        }
        self._docking_position_tolerance = docking_position_tolerance
        self._announced: dict[str, StationLease] = {}

    @property
    def status_topics(self) -> tuple[str, ...]:
        return tuple(codec.status_topic for codec in self._codecs.values())

    def synchronize_leases(self, *, now: float) -> None:
        active = {
            lease.lease_id: lease for lease in self._api.service.active_station_leases(now=now)
        }
        for lease_id, lease in active.items():
            if lease_id not in self._announced:
                topic, payload = self._codecs[lease.station_id].entry_request_message(lease)
                self._publisher.publish(topic, payload, qos=1, retain=False)
        for lease_id, lease in tuple(self._announced.items()):
            if lease_id not in active:
                topic, payload = self._codecs[lease.station_id].release_message(lease)
                self._publisher.publish(topic, payload, qos=1, retain=False)
        self._announced = active

    def handle_status(
        self,
        topic: str,
        payload: str,
        *,
        received_at: float,
    ) -> StationAutomationResult:
        codec = self._codec_for_status_topic(topic)
        snapshot = codec.snapshot_from_message(topic, payload, received_at=received_at)
        lease = self._lease_for_snapshot(snapshot.station_id, snapshot.lease_id, now=received_at)
        decision = self._bridges[snapshot.station_id].reconcile(
            snapshot,
            lease_id=lease.lease_id,
            robot_id=lease.robot_id,
            mission_id=lease.mission_id,
            now=received_at,
        )
        mission = self._api.service.mission(lease.mission_id)
        robot = next(
            (item for item in self._api.service.robots() if item.robot_id == lease.robot_id),
            None,
        )
        within_tolerance = (
            robot is not None
            and robot.pose.distance_to(mission.current_stop.approach_pose)
            <= self._docking_position_tolerance
        )
        if (
            mission.state is MissionState.AWAITING_STATION
            and decision.docking_authorized
            and within_tolerance
        ):
            self._api.start_docking(
                mission.mission_id,
                {"lease_id": lease.lease_id, "now": received_at},
            )
        if mission.state is MissionState.DOCKING and decision.transfer_authorized:
            self._api.confirm_docked(
                mission.mission_id,
                {"lease_id": lease.lease_id, "now": received_at},
            )
        if mission.state is MissionState.TRANSFERRING and decision.transfer_complete:
            self._api.complete_transfer(
                mission.mission_id,
                {"lease_id": lease.lease_id, "now": received_at},
            )
        return StationAutomationResult(
            snapshot.station_id,
            mission.mission_id,
            mission.state,
            decision,
            within_tolerance,
        )

    def _codec_for_status_topic(self, topic: str) -> MqttStationCodec:
        for codec in self._codecs.values():
            if topic == codec.status_topic:
                return codec
        raise ValueError(f"unexpected station status topic: {topic}")

    def _lease_for_snapshot(
        self,
        station_id: str,
        lease_id: str | None,
        *,
        now: float,
    ) -> StationLease:
        if lease_id is None:
            raise LeaseInvalid("PLC status is missing lease correlation")
        for lease in self._api.service.active_station_leases(now=now):
            if lease.station_id == station_id and lease.lease_id == lease_id:
                return lease
        raise NotFound(f"no active fleet lease matches station {station_id}")


class MqttPlcStationSimulator:
    """Network-facing station simulator with deterministic automatic transfer."""

    def __init__(self, station_id: str) -> None:
        self.codec = MqttStationCodec(station_id)
        self._lease: dict[str, Any] | None = None
        self._faulted = False

    @property
    def command_topic(self) -> str:
        return self.codec.command_topic

    def handle_command(self, topic: str, payload: str, *, now: float) -> tuple[str, str]:
        if topic != self.codec.command_topic:
            raise ValueError(f"unexpected station command topic: {topic}")
        body = json.loads(payload)
        if not isinstance(body, dict):
            raise ValueError("station command payload must be an object")
        command = str(body.get("command", ""))
        station_id = str(body.get("station_id", ""))
        if station_id != self.codec.station_id:
            raise ValueError(f"command belongs to station {station_id}")
        if command == "entry_request":
            self._require_fields(body, ("robot_id", "mission_id", "lease_id"))
            self._lease = dict(body)
        elif command == "release":
            if self._lease is not None and body.get("lease_id") == self._lease.get("lease_id"):
                self._lease = None
        elif command == "restart":
            self._lease = None
            self._faulted = False
        elif command == "fault":
            self._faulted = bool(body.get("active", True))
        else:
            raise ValueError(f"unsupported station command: {command}")
        return self.status_message(now=now)

    def status_message(self, *, now: float) -> tuple[str, str]:
        lease_id = None if self._lease is None else self._lease.get("lease_id")
        granted = self._lease is not None and not self._faulted
        return (
            self.codec.status_topic,
            json.dumps(
                {
                    "station_id": self.codec.station_id,
                    "heartbeat_at": now,
                    "entry_granted": granted,
                    "transfer_ready": granted,
                    "transfer_complete": granted,
                    "faulted": self._faulted,
                    "lease_id": lease_id,
                },
                sort_keys=True,
            ),
        )

    def _require_fields(self, payload: dict[str, Any], fields: tuple[str, ...]) -> None:
        missing = [field for field in fields if not str(payload.get(field, "")).strip()]
        if missing:
            raise ValueError(f"station command is missing fields: {', '.join(missing)}")
