"""Verification of bounded and permission-aware pseudo-docking commands."""

import math
import unittest

from amr_fleet_core import Pose2D
from amr_fleet_core.docking import DockingPhase, PseudoDockingController


class PseudoDockingControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = PseudoDockingController()
        self.target = Pose2D(1.0, 0.0, 0.0)

    def test_missing_station_authorization_holds_zero_velocity(self) -> None:
        command = self.controller.command(
            Pose2D(0.0, 0.0, 0.0),
            self.target,
            station_authorized=False,
        )
        self.assertEqual(DockingPhase.HOLD, command.phase)
        self.assertEqual((0.0, 0.0), (command.linear_x, command.angular_z))

    def test_controller_aligns_approaches_and_confirms_pose_tolerance(self) -> None:
        align = self.controller.command(
            Pose2D(0.0, 0.0, math.pi / 2.0),
            self.target,
            station_authorized=True,
        )
        approach = self.controller.command(
            Pose2D(0.5, 0.0, 0.0),
            self.target,
            station_authorized=True,
        )
        docked = self.controller.command(
            Pose2D(0.98, 0.0, math.radians(1.0)),
            self.target,
            station_authorized=True,
        )
        self.assertEqual(DockingPhase.ALIGN, align.phase)
        self.assertEqual(0.0, align.linear_x)
        self.assertEqual(DockingPhase.APPROACH, approach.phase)
        self.assertGreater(approach.linear_x, 0.0)
        self.assertEqual(DockingPhase.DOCKED, docked.phase)

    def test_commands_remain_inside_commissioned_bounds(self) -> None:
        command = self.controller.command(
            Pose2D(-10.0, 5.0, -math.pi),
            self.target,
            station_authorized=True,
        )
        self.assertLessEqual(abs(command.linear_x), self.controller.max_linear_speed)
        self.assertLessEqual(abs(command.angular_z), self.controller.max_angular_speed)


if __name__ == "__main__":
    unittest.main()
