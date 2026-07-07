"""Verification of Grafana dashboard artifact generation."""

import json
from pathlib import Path
import unittest

from amr_fleet_core.grafana import build_grafana_dashboard, validate_grafana_dashboard


class GrafanaDashboardTests(unittest.TestCase):
    def test_dashboard_contains_required_fleet_observability_panels(self) -> None:
        dashboard = build_grafana_dashboard(datasource_uid="test-influx")
        validate_grafana_dashboard(dashboard)

        panel_titles = {panel["title"] for panel in dashboard["panels"]}
        self.assertIn("Robot Battery", panel_titles)
        self.assertIn("Robot Telemetry Age", panel_titles)
        self.assertIn("Mission Revisions", panel_titles)
        self.assertIn("Station Lease Expiry", panel_titles)
        self.assertEqual(dashboard["panels"][0]["datasource"]["uid"], "test-influx")

    def test_dashboard_validation_rejects_missing_required_panels(self) -> None:
        dashboard = build_grafana_dashboard()
        dashboard["panels"] = dashboard["panels"][:-1]

        with self.assertRaises(ValueError):
            validate_grafana_dashboard(dashboard)

    def test_committed_dashboard_artifact_is_valid(self) -> None:
        repo_root = Path(__file__).resolve().parents[4]
        dashboard_path = repo_root / "dashboards" / "grafana" / "amr-fleet-overview.json"
        dashboard = json.loads(dashboard_path.read_text(encoding="utf-8"))

        validate_grafana_dashboard(dashboard)


if __name__ == "__main__":
    unittest.main()
