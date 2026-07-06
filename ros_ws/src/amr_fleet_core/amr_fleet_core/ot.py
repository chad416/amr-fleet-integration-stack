"""Industrial station bridge and PLC handshake reconciliation."""

from __future__ import annotations

from dataclasses import dataclass

from .errors import LeaseInvalid
from .station import StationAccessManager, StationLease


@dataclass(frozen=True, slots=True)
class StationPlcSnapshot:
    station_id: str
    heartbeat_at: float
    entry_granted: bool = False
    transfer_ready: bool = False
    transfer_complete: bool = False
    faulted: bool = False
    lease_id: str | None = None


@dataclass(frozen=True, slots=True)
class StationBridgeDecision:
    station_id: str
    lease_id: str
    docking_authorized: bool
    transfer_authorized: bool
    transfer_complete: bool
    reason: str


class PlcStationSimulator:
    """Deterministic in-process material-handling PLC handshake simulator."""

    def __init__(self, station_id: str) -> None:
        if not station_id.strip():
            raise ValueError("station_id must be non-empty")
        self.station_id = station_id
        self._lease_id: str | None = None
        self._entry_granted = False
        self._transfer_ready = False
        self._transfer_complete = False
        self._faulted = False
        self._heartbeat_at = 0.0

    def receive_entry_request(self, lease: StationLease, *, now: float) -> None:
        if lease.station_id != self.station_id:
            raise LeaseInvalid("entry request targets a different station")
        self._lease_id = lease.lease_id
        self._entry_granted = False
        self._transfer_ready = False
        self._transfer_complete = False
        self._faulted = False
        self._heartbeat_at = now

    def grant_entry(self, *, now: float) -> None:
        self._require_active_request()
        self._entry_granted = True
        self._heartbeat_at = now

    def mark_transfer_ready(self, *, now: float) -> None:
        self._require_entry_granted()
        self._transfer_ready = True
        self._heartbeat_at = now

    def mark_transfer_complete(self, *, now: float) -> None:
        self._require_entry_granted()
        self._transfer_ready = True
        self._transfer_complete = True
        self._heartbeat_at = now

    def set_faulted(self, faulted: bool, *, now: float) -> None:
        self._faulted = faulted
        self._heartbeat_at = now

    def restart(self, *, now: float) -> None:
        self._lease_id = None
        self._entry_granted = False
        self._transfer_ready = False
        self._transfer_complete = False
        self._faulted = False
        self._heartbeat_at = now

    def snapshot(self) -> StationPlcSnapshot:
        return StationPlcSnapshot(
            station_id=self.station_id,
            heartbeat_at=self._heartbeat_at,
            entry_granted=self._entry_granted,
            transfer_ready=self._transfer_ready,
            transfer_complete=self._transfer_complete,
            faulted=self._faulted,
            lease_id=self._lease_id,
        )

    def _require_active_request(self) -> None:
        if self._lease_id is None:
            raise LeaseInvalid("PLC has no active entry request")

    def _require_entry_granted(self) -> None:
        self._require_active_request()
        if not self._entry_granted:
            raise LeaseInvalid("PLC entry has not been granted")


class StationBridge:
    """Reconciles fleet leases with PLC state before movement is authorized."""

    def __init__(
        self,
        station_access: StationAccessManager,
        *,
        plc_stale_after: float,
    ) -> None:
        if plc_stale_after <= 0.0:
            raise ValueError("plc_stale_after must be positive")
        self._station_access = station_access
        self._plc_stale_after = plc_stale_after

    def request_entry(
        self,
        station_id: str,
        robot_id: str,
        mission_id: str,
        *,
        now: float,
    ) -> StationLease:
        return self._station_access.acquire(
            station_id,
            robot_id,
            mission_id,
            now=now,
        )

    def reconcile(
        self,
        snapshot: StationPlcSnapshot,
        *,
        lease_id: str,
        robot_id: str,
        mission_id: str,
        now: float,
    ) -> StationBridgeDecision:
        self._reject_stale_or_faulted(snapshot, now=now)
        lease = self._station_access.validate(
            snapshot.station_id,
            lease_id,
            robot_id,
            mission_id,
            now=now,
        )
        if snapshot.lease_id is not None and snapshot.lease_id != lease.lease_id:
            raise LeaseInvalid("PLC lease correlation does not match fleet lease")
        docking_authorized = snapshot.entry_granted
        transfer_authorized = docking_authorized and snapshot.transfer_ready
        return StationBridgeDecision(
            station_id=snapshot.station_id,
            lease_id=lease.lease_id,
            docking_authorized=docking_authorized,
            transfer_authorized=transfer_authorized,
            transfer_complete=transfer_authorized and snapshot.transfer_complete,
            reason="grant valid" if docking_authorized else "waiting for station grant",
        )

    def _reject_stale_or_faulted(self, snapshot: StationPlcSnapshot, *, now: float) -> None:
        age = max(0.0, now - snapshot.heartbeat_at)
        if age > self._plc_stale_after:
            raise LeaseInvalid("PLC heartbeat is stale; docking inhibited")
        if snapshot.faulted:
            raise LeaseInvalid("PLC reports station fault; docking inhibited")
