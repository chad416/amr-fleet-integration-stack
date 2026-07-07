#!/usr/bin/env python3
"""Run and persist the complete non-hardware software acceptance campaign."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CORE_SOURCE = REPOSITORY_ROOT / "ros_ws" / "src" / "amr_fleet_core"
sys.path.insert(0, str(CORE_SOURCE))

from amr_fleet_core.software_acceptance import run_software_acceptance  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=100)
    parser.add_argument("--revision", default="worktree")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/software-acceptance"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    generated_at = datetime.now(UTC)
    result = {
        "generated_at": generated_at.isoformat(),
        "revision": args.revision,
        "campaign": run_software_acceptance(runs=args.runs),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / f"software-acceptance-{generated_at:%Y%m%dT%H%M%SZ}.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({**result, "evidence": str(output)}, indent=2, sort_keys=True))
    return 0 if result["campaign"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
