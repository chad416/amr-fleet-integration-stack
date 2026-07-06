"""Verification of the aggregate non-hardware acceptance campaign."""

import unittest

from amr_fleet_core.software_acceptance import run_software_acceptance


class SoftwareAcceptanceTests(unittest.TestCase):
    def test_all_non_hardware_campaigns_pass(self) -> None:
        result = run_software_acceptance(runs=5)
        self.assertTrue(result["passed"])
        self.assertEqual(5, result["station_mqtt_pseudo_docking"]["completed"])
        self.assertEqual(0, result["traffic_coordination"]["deadlocks"])


if __name__ == "__main__":
    unittest.main()
