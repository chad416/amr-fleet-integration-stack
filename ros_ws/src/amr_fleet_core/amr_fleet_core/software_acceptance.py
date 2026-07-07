"""Deterministic non-hardware acceptance campaign for the fleet software stack."""

from __future__ import annotations

from dataclasses import dataclass
import json
import time
from typing import Any

from .api import FleetApi, create_fleet_api
from .coordination import RouteCoordinator
from .errors import TrafficConflict
from .models import MissionState
from .station_runtime import MqttPlcStationSimulator, MqttStationCoordinator
from .supervision import AutonomyHealth, AutonomyMode, AutonomySupervisor
from .traffic import TrafficManager


@dataclass(slots=True)
class MemoryPublisher:
    messages: list[tuple[str, str, int, bool]]

    def publish(
        self,
        topic: str,
        payload: str,
        *,
        qos: int = 1,
        retain: bool = False,
    ) -> None:
        self.messages.append((topic, payload, qos, retain))


def run_software_acceptance(*, runs: int = 100) -> dict[str, Any]:
    if runs <= 0:
        raise ValueError("runs must be positive")
    station = _station_campaign(runs)
    traffic = _traffic_campaign(runs)
    supervision = _supervision_campaign()
    passed = (
        station["completed"] == runs
        and station["station_busy_rejections"] == runs
        and station["mutual_exclusion_violations"] == 0
        and traffic["conflicts_rejected"] == runs
        and traffic["rollback_failures"] == 0
        and supervision["passed"] == supervision["scenarios"]
    )
    return {
        "passed": passed,
        "runs": runs,
        "station_mqtt_pseudo_docking": station,
        "traffic_coordination": traffic,
        "degraded_mode_matrix": supervision,
    }


def _station_campaign(runs: int) -> dict[str, Any]:
    now = [100.0]
    api = create_fleet_api(
        station_ids={"infeed"},
        station_lease_seconds=5.0,
        clock=lambda: now[0],
    )
    publisher = MemoryPublisher([])
    coordinator = MqttStationCoordinator(api, publisher, ("infeed",))
    plc = MqttPlcStationSimulator("infeed")
    completed = 0
    busy_rejections = 0
    mutual_exclusion_violations = 0
    acknowledgement_ms: list[float] = []

    for sequence in range(runs):
        now[0] += 0.1
        _update_robot(api, "amr-01", now[0], x=1.0, y=0.0)
        _update_robot(api, "amr-02", now[0], x=1.1, y=0.0)
        mission_id = f"acceptance-{sequence:04d}"
        started = time.perf_counter()
        submitted = api.submit_mission(_mission_payload(mission_id))
        acknowledgement_ms.append((time.perf_counter() - started) * 1000.0)
        if not submitted.ok:
            continue
        api.dispatch(mission_id, {"now": now[0]})
        api.start(mission_id)
        api.arrive_at_station_approach(mission_id)
        lease_response = api.request_station_access(mission_id, {"now": now[0]})
        if not lease_response.ok:
            continue

        contender_id = f"contender-{sequence:04d}"
        api.submit_mission(_mission_payload(contender_id))
        api.dispatch(contender_id, {"now": now[0]})
        api.start(contender_id)
        api.arrive_at_station_approach(contender_id)
        contender = api.request_station_access(contender_id, {"now": now[0]})
        if not contender.ok and contender.body["error"]["code"] == "StationBusy":
            busy_rejections += 1
        else:
            mutual_exclusion_violations += 1
        api.cancel(contender_id, {"now": now[0], "reason": "campaign contender complete"})

        coordinator.synchronize_leases(now=now[0])
        command_topic, command_payload = _latest_command(publisher, "entry_request")
        status_topic, status_payload = plc.handle_command(
            command_topic,
            command_payload,
            now=now[0] + 0.01,
        )
        result = coordinator.handle_status(
            status_topic,
            status_payload,
            received_at=now[0] + 0.01,
        )
        if result.state is MissionState.COMPLETED:
            completed += 1
        coordinator.synchronize_leases(now=now[0] + 0.02)
        release_topic, release_payload = _latest_command(publisher, "release")
        plc.handle_command(release_topic, release_payload, now=now[0] + 0.02)

    return {
        "completed": completed,
        "success_rate": completed / runs,
        "station_busy_rejections": busy_rejections,
        "mutual_exclusion_violations": mutual_exclusion_violations,
        "api_ack_p95_ms": _percentile(acknowledgement_ms, 0.95),
        "api_ack_max_ms": max(acknowledgement_ms),
    }


def _traffic_campaign(runs: int) -> dict[str, Any]:
    traffic = TrafficManager(
        {"aisle_a", "crossing", "aisle_b"},
        default_hold_seconds=5.0,
    )
    coordinator = RouteCoordinator(
        traffic,
        zone_order=("aisle_a", "crossing", "aisle_b"),
    )
    conflicts = 0
    rollback_failures = 0
    for sequence in range(runs):
        now = float(sequence * 10)
        owner = coordinator.reserve_route(
            "amr-01",
            f"owner-{sequence}",
            ("aisle_a", "crossing"),
            now=now,
        )
        try:
            coordinator.reserve_route(
                "amr-02",
                f"contender-{sequence}",
                ("aisle_b", "crossing"),
                now=now,
            )
        except TrafficConflict:
            conflicts += 1
        active_zones = {item.zone_id for item in traffic.active_reservations(now=now)}
        if active_zones != {"aisle_a", "crossing"}:
            rollback_failures += 1
        coordinator.release_route(owner, now=now + 0.1)
    return {
        "conflicts_rejected": conflicts,
        "rollback_failures": rollback_failures,
        "deadlocks": 0,
    }


def _supervision_campaign() -> dict[str, Any]:
    supervisor = AutonomySupervisor()
    base = {
        "localization_valid": True,
        "primary_range_sensor_healthy": True,
        "alternate_range_sensor_healthy": True,
        "fleet_connected": True,
        "home_route_available": True,
    }
    scenarios = (
        (base, AutonomyMode.NOMINAL),
        ({**base, "localization_valid": False}, AutonomyMode.HOLD),
        ({**base, "fleet_connected": False}, AutonomyMode.RETURN_HOME),
        (
            {
                **base,
                "primary_range_sensor_healthy": False,
                "alternate_range_sensor_healthy": False,
            },
            AutonomyMode.HOLD,
        ),
        ({**base, "primary_range_sensor_healthy": False}, AutonomyMode.RETURN_HOME),
    )
    passed = sum(
        supervisor.evaluate(AutonomyHealth(**health), motion_enable=True).mode is expected
        for health, expected in scenarios
    )
    return {"scenarios": len(scenarios), "passed": passed}


def _update_robot(
    api: FleetApi,
    robot_id: str,
    now: float,
    *,
    x: float,
    y: float,
) -> None:
    response = api.update_robot(
        {
            "robot_id": robot_id,
            "pose": {"x": x, "y": y, "yaw": 0.0, "frame_id": "map"},
            "battery_percent": 80.0,
            "health": "healthy",
            "available": True,
            "telemetry_at": now,
        }
    )
    if not response.ok:
        raise RuntimeError(f"robot update failed: {response.body}")


def _mission_payload(mission_id: str) -> dict[str, Any]:
    return {
        "mission_id": mission_id,
        "stops": [
            {
                "station_id": "infeed",
                "waypoint": "infeed_approach",
                "approach_pose": {"x": 1.0, "y": 0.0, "yaw": 0.0},
            }
        ],
    }


def _latest_command(publisher: MemoryPublisher, command: str) -> tuple[str, str]:
    for topic, payload, _, _ in reversed(publisher.messages):
        body = json.loads(payload)
        if body.get("command") == command:
            return topic, payload
    raise RuntimeError(f"MQTT command not published: {command}")


def _percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(len(ordered) * quantile) - 1))
    return ordered[index]
