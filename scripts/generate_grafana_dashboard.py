#!/usr/bin/env python3
"""Generate the AMR fleet Grafana dashboard JSON artifact."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = REPO_ROOT / "ros_ws" / "src" / "amr_fleet_core"
sys.path.insert(0, str(CORE_SRC))

from amr_fleet_core.grafana import (  # noqa: E402
    build_grafana_dashboard,
    validate_grafana_dashboard,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "dashboards" / "grafana" / "amr-fleet-overview.json",
    )
    parser.add_argument("--datasource-uid", default="influxdb")
    args = parser.parse_args()

    dashboard = build_grafana_dashboard(datasource_uid=args.datasource_uid)
    validate_grafana_dashboard(dashboard)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(dashboard, indent=2, sort_keys=True), encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
