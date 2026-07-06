#!/usr/bin/env python3
"""Run the Gate 3 fleet API benchmark and recovery evidence scenario."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = REPO_ROOT / "ros_ws" / "src" / "amr_fleet_core"
sys.path.insert(0, str(CORE_SRC))

from amr_fleet_core import create_fleet_api  # noqa: E402


def robot_payload(now: float) -> dict[str, Any]:
    return {
        "robot_id": "amr-01",
        "pose": {"x": 0.0, "y": 0.0, "yaw": 0.0, "frame_id": "map"},
        "battery_percent": 88.0,
        "health": "healthy",
        "available": True,
        "telemetry_at": now,
    }


def mission_payload(mission_id: str) -> dict[str, Any]:
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


def run_benchmark(runs: int) -> dict[str, Any]:
    api = create_fleet_api(
        station_ids={"infeed"},
        station_lease_seconds=10.0,
        telemetry_stale_after=3.0,
        recovery_max_attempts=2,
    )
    durations_ms: list[float] = []
    completed = 0

    def call(name: str, fn: Any) -> Any:
        start = time.perf_counter()
        response = fn()
        durations_ms.append((time.perf_counter() - start) * 1000.0)
        if not response.ok:
            raise RuntimeError(f"{name} failed: {response.body}")
        return response

    for index in range(runs):
        now = 1000.0 + index * 20.0
        mission_id = f"bench-{index:03d}"
        call("update_robot", lambda now=now: api.update_robot(robot_payload(now)))
        call(
            "submit_mission",
            lambda mission_id=mission_id: api.submit_mission(mission_payload(mission_id)),
        )
        call(
            "dispatch",
            lambda mission_id=mission_id, now=now: api.dispatch(
                mission_id,
                {"now": now + 1.0},
            ),
        )
        call("start", lambda mission_id=mission_id: api.start(mission_id))
        call("arrive", lambda mission_id=mission_id: api.arrive_at_station_approach(mission_id))
        lease = call(
            "station_access",
            lambda mission_id=mission_id, now=now: api.request_station_access(
                mission_id,
                {"now": now + 2.0},
            ),
        ).body["lease"]["lease_id"]
        call(
            "start_docking",
            lambda mission_id=mission_id, lease=lease, now=now: api.start_docking(
                mission_id,
                {"lease_id": lease, "now": now + 3.0},
            ),
        )
        call(
            "confirm_docked",
            lambda mission_id=mission_id, lease=lease, now=now: api.confirm_docked(
                mission_id,
                {"lease_id": lease, "now": now + 4.0},
            ),
        )
        done = call(
            "complete_transfer",
            lambda mission_id=mission_id, lease=lease, now=now: api.complete_transfer(
                mission_id,
                {"lease_id": lease, "now": now + 5.0},
            ),
        )
        if done.body["mission"]["state"] == "completed":
            completed += 1

    p95 = statistics.quantiles(durations_ms, n=100)[94] if durations_ms else 0.0
    return {
        "runs": runs,
        "completed": completed,
        "success_rate": completed / runs,
        "api_ack_p95_ms": p95,
        "api_ack_max_ms": max(durations_ms) if durations_ms else 0.0,
        "events_recorded": len(api.telemetry(now=1000.0 + runs * 20.0).body["events"]),
    }


def run_recovery_evidence() -> dict[str, Any]:
    api = create_fleet_api(
        station_ids={"infeed"},
        station_lease_seconds=10.0,
        telemetry_stale_after=3.0,
        recovery_max_attempts=2,
    )
    api.update_robot(robot_payload(2000.0))
    api.submit_mission(mission_payload("recovery-evidence"))
    api.dispatch("recovery-evidence", {"now": 2001.0})
    api.start("recovery-evidence")
    first = api.begin_recovery(
        "recovery-evidence",
        {"now": 2002.0, "reason": "blocked path"},
    )
    api.complete_recovery("recovery-evidence")
    second = api.begin_recovery(
        "recovery-evidence",
        {"now": 2003.0, "reason": "planner timeout"},
    )
    api.complete_recovery("recovery-evidence")
    exhausted = api.begin_recovery(
        "recovery-evidence",
        {"now": 2004.0, "reason": "blocked after bounded recovery"},
    )
    mission = api.mission("recovery-evidence").body["mission"]
    return {
        "first_attempt": first.body["attempt"],
        "second_attempt": second.body["attempt"],
        "third_attempt_accepted": exhausted.ok,
        "third_attempt_error": exhausted.body["error"]["code"],
        "final_state": mission["state"],
        "failure_reason": mission["failure_reason"],
    }


def write_evidence(report: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output = output_dir / f"fleet-api-benchmark-{timestamp}.json"
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=100)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if args.runs <= 0:
        raise SystemExit("--runs must be positive")

    output_dir = args.output_dir or Path(tempfile.gettempdir()) / "amr_fleet_api_benchmark"
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "benchmark": run_benchmark(args.runs),
        "recovery": run_recovery_evidence(),
    }
    output = write_evidence(report, output_dir)
    print(json.dumps({"evidence": str(output), **report}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
