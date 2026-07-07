#!/usr/bin/env python3
"""Run the repeatable L0 fleet fault campaign."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
import tempfile

REPO_ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = REPO_ROOT / "ros_ws" / "src" / "amr_fleet_core"
sys.path.insert(0, str(CORE_SRC))

from amr_fleet_core.fault_campaign import campaign_summary, run_l0_fault_campaign  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    output_dir = args.output_dir or Path(tempfile.gettempdir()) / "amr_fleet_fault_campaign"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output = output_dir / f"fleet-fault-campaign-{timestamp}.json"

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "campaign": campaign_summary(run_l0_fault_campaign()),
    }
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"evidence": str(output), **report}, indent=2, sort_keys=True))
    return 0 if report["campaign"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
