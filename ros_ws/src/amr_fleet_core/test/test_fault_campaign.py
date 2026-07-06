"""Verification of the repeatable L0 fault campaign."""

import unittest

from amr_fleet_core.fault_campaign import campaign_summary, run_l0_fault_campaign


class FaultCampaignTests(unittest.TestCase):
    def test_all_l0_fault_campaign_scenarios_pass(self) -> None:
        summary = campaign_summary(run_l0_fault_campaign())

        self.assertEqual(summary["scenarios"], 5)
        self.assertEqual(summary["failed"], 0)
        self.assertEqual(summary["success_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
