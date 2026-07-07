"""Static acceptance of the reproducible OT/IT container deployment."""

import json
from pathlib import Path
import unittest

import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


class DeploymentContractTests(unittest.TestCase):
    def test_compose_stack_contains_health_checked_runtime_services(self) -> None:
        compose = yaml.safe_load((REPOSITORY_ROOT / "compose.yaml").read_text())
        services = compose["services"]
        required = {"mqtt", "influxdb", "fleet-api", "grafana"}
        self.assertLessEqual(required, services.keys())
        self.assertTrue(
            {"station-infeed", "station-outfeed", "station-charger"}
            <= services.keys()
        )
        for name in required:
            self.assertIn("healthcheck", services[name], name)
        self.assertEqual("127.0.0.1:1883:1883", services["mqtt"]["ports"][0])

    def test_grafana_provisioning_matches_dashboard_datasource(self) -> None:
        datasource = yaml.safe_load(
            (
                REPOSITORY_ROOT
                / "deployment/grafana/provisioning/datasources/influxdb.yaml"
            ).read_text()
        )
        dashboard = json.loads(
            (REPOSITORY_ROOT / "dashboards/grafana/amr-fleet-overview.json").read_text()
        )
        self.assertEqual("influxdb", datasource["datasources"][0]["uid"])
        panel_uids = {
            panel["datasource"]["uid"]
            for panel in dashboard["panels"]
            if "datasource" in panel
        }
        self.assertEqual({"influxdb"}, panel_uids)

    def test_runtime_container_drops_root_privileges(self) -> None:
        dockerfile = (REPOSITORY_ROOT / "deployment/Dockerfile").read_text()
        self.assertIn("USER 10001:10001", dockerfile)
        self.assertIn('CMD ["amr-fleet-server"]', dockerfile)


if __name__ == "__main__":
    unittest.main()
