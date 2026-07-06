"""Repeatable L0 fleet fault campaign scenarios."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .api import FleetApi, create_fleet_api
from .errors import LeaseInvalid
from .models import Pose2D
from .ot import StationBridge, StationPlcSnapshot
from .station import StationAccessManager


@dataclass(frozen=True, slots=True)
class FaultScenarioResult:
    scenario_id: str
    passed: bool
    detail: str
    evidence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "passed": self.passed,
            "detail": self.detail,
            "evidence": dict(self.evidence),
        }


def run_l0_fault_campaign() -> tuple[FaultScenarioResult, ...]:
    return (
        _stale_robot_rejected(),
        _station_busy_rejected(),
        _plc_stale_heartbeat_inhibits_docking(),
        _bounded_recovery_exhausts_to_failed(),
        _batch_dispatch_assigns_idle_fleet(),
    )


def campaign_summary(results: tuple[FaultScenarioResult, ...]) -> dict[str, Any]:
    passed = sum(1 for result in results if result.passed)
    return {
        "scenarios": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "success_rate": passed / len(results) if results else 0.0,
        "results": [result.to_dict() for result in results],
    }


def _stale_robot_rejected() -> FaultScenarioResult:
    api = create_fleet_api(station_ids={"infeed"}, telemetry_stale_after=3.0)
    api.update_robot(_robot_payload("amr-01", x=0.0, telemetry_at=100.0))
    api.submit_mission(_mission_payload("stale-robot", "infeed", 1.0))
    response = api.dispatch("stale-robot", {"now": 104.1})
    return FaultScenarioResult(
        scenario_id="L0-FAULT-STALE-ROBOT",
        passed=not response.ok and response.body["error"]["code"] == "NoEligibleRobot",
        detail="Stale robot telemetry must exclude the robot from dispatch.",
        evidence={"response": response.body},
    )


def _station_busy_rejected() -> FaultScenarioResult:
    api = _two_robot_api()
    api.submit_mission(_mission_payload("station-owner", "infeed", 1.0))
    api.submit_mission(_mission_payload("station-contender", "infeed", 2.0))
    api.dispatch("station-owner", {"now": 101.0})
    api.dispatch("station-contender", {"now": 101.0})
    api.start("station-owner")
    api.start("station-contender")
    api.arrive_at_station_approach("station-owner")
    api.arrive_at_station_approach("station-contender")
    first = api.request_station_access("station-owner", {"now": 102.0})
    second = api.request_station_access("station-contender", {"now": 102.1})
    return FaultScenarioResult(
        scenario_id="L0-FAULT-STATION-BUSY",
        passed=first.ok and not second.ok and second.body["error"]["code"] == "StationBusy",
        detail="A second robot cannot acquire a live station lease.",
        evidence={"owner": first.body, "contender": second.body},
    )


def _plc_stale_heartbeat_inhibits_docking() -> FaultScenarioResult:
    station_access = StationAccessManager({"infeed"}, default_lease_seconds=10.0)
    bridge = StationBridge(station_access, plc_stale_after=1.0)
    lease = bridge.request_entry("infeed", "amr-01", "mission-plc", now=100.0)
    try:
        bridge.reconcile(
            StationPlcSnapshot(
                station_id="infeed",
                heartbeat_at=100.0,
                entry_granted=True,
                lease_id=lease.lease_id,
            ),
            lease_id=lease.lease_id,
            robot_id="amr-01",
            mission_id="mission-plc",
            now=102.0,
        )
    except LeaseInvalid as error:
        return FaultScenarioResult(
            scenario_id="L0-FAULT-PLC-STALE",
            passed=True,
            detail="Stale PLC heartbeat inhibited docking.",
            evidence={"error": error.__class__.__name__, "message": str(error)},
        )
    return FaultScenarioResult(
        scenario_id="L0-FAULT-PLC-STALE",
        passed=False,
        detail="Stale PLC heartbeat was incorrectly accepted.",
        evidence={},
    )


def _bounded_recovery_exhausts_to_failed() -> FaultScenarioResult:
    api = create_fleet_api(
        station_ids={"infeed"},
        telemetry_stale_after=3.0,
        recovery_max_attempts=2,
    )
    api.update_robot(_robot_payload("amr-01", x=0.0, telemetry_at=100.0))
    api.submit_mission(_mission_payload("recovery-fault", "infeed", 1.0))
    api.dispatch("recovery-fault", {"now": 101.0})
    api.start("recovery-fault")
    api.begin_recovery("recovery-fault", {"now": 102.0, "reason": "blocked path"})
    api.complete_recovery("recovery-fault")
    api.begin_recovery("recovery-fault", {"now": 103.0, "reason": "blocked again"})
    api.complete_recovery("recovery-fault")
    third = api.begin_recovery(
        "recovery-fault",
        {"now": 104.0, "reason": "still blocked"},
    )
    mission = api.mission("recovery-fault").body["mission"]
    return FaultScenarioResult(
        scenario_id="L0-FAULT-RECOVERY-EXHAUSTED",
        passed=not third.ok and mission["state"] == "failed",
        detail="Recovery budget exhaustion must fail safe.",
        evidence={"third_attempt": third.body, "mission": mission},
    )


def _batch_dispatch_assigns_idle_fleet() -> FaultScenarioResult:
    api = _two_robot_api()
    api.submit_mission(_mission_payload("batch-a", "infeed", 1.0))
    api.submit_mission(_mission_payload("batch-b", "outfeed", 9.0))
    response = api.dispatch_all({"now": 101.0})
    assignments = response.body["assignments"] if response.ok else []
    return FaultScenarioResult(
        scenario_id="L0-FLEET-BATCH-DISPATCH",
        passed=response.ok
        and assignments
        == [
            {"mission_id": "batch-a", "robot_id": "amr-01"},
            {"mission_id": "batch-b", "robot_id": "amr-02"},
        ],
        detail="Queued missions are assigned across idle eligible robots.",
        evidence={"response": response.body},
    )


def _two_robot_api() -> FleetApi:
    api = create_fleet_api(station_ids={"infeed", "outfeed"}, telemetry_stale_after=3.0)
    api.update_robot(_robot_payload("amr-01", x=0.0, telemetry_at=100.0))
    api.update_robot(_robot_payload("amr-02", x=10.0, telemetry_at=100.0))
    return api


def _robot_payload(robot_id: str, *, x: float, telemetry_at: float) -> dict[str, Any]:
    return {
        "robot_id": robot_id,
        "pose": {"x": x, "y": 0.0},
        "battery_percent": 90.0,
        "health": "healthy",
        "available": True,
        "telemetry_at": telemetry_at,
    }


def _mission_payload(mission_id: str, station_id: str, x: float) -> dict[str, Any]:
    return {
        "mission_id": mission_id,
        "stops": [
            {
                "station_id": station_id,
                "waypoint": f"{station_id}_approach",
                "approach_pose": _pose_payload(x),
            }
        ],
    }


def _pose_payload(x: float) -> dict[str, Any]:
    pose = Pose2D(x, 0.0)
    return {"x": pose.x, "y": pose.y, "yaw": pose.yaw, "frame_id": pose.frame_id}
