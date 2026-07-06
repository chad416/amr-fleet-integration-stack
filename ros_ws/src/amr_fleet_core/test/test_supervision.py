"""Verification of degraded autonomy modes and motion-enable separation."""

import unittest

from amr_fleet_core.supervision import (
    AutonomyHealth,
    AutonomyMode,
    AutonomySupervisor,
    MotionEnableInterlock,
)


def healthy(**overrides: bool) -> AutonomyHealth:
    values = {
        "localization_valid": True,
        "primary_range_sensor_healthy": True,
        "alternate_range_sensor_healthy": True,
        "fleet_connected": True,
        "home_route_available": True,
        "emergency_stop_active": False,
    }
    values.update(overrides)
    return AutonomyHealth(**values)


class AutonomySupervisorTests(unittest.TestCase):
    def test_estop_reset_never_implies_permission_to_move(self) -> None:
        interlock = MotionEnableInterlock()
        interlock.operator_start()
        self.assertTrue(interlock.motion_permitted)

        interlock.set_emergency_stop(True)
        self.assertFalse(interlock.motion_permitted)
        interlock.set_emergency_stop(False)
        self.assertFalse(interlock.motion_permitted)

        interlock.operator_start()
        self.assertTrue(interlock.motion_permitted)

    def test_degraded_sensor_path_returns_home_only_with_healthy_alternate(self) -> None:
        supervisor = AutonomySupervisor()
        decision = supervisor.evaluate(
            healthy(primary_range_sensor_healthy=False),
            motion_enable=True,
        )
        self.assertEqual(AutonomyMode.RETURN_HOME, decision.mode)
        self.assertFalse(decision.accept_new_missions)
        self.assertTrue(decision.motion_permitted)

        decision = supervisor.evaluate(
            healthy(
                primary_range_sensor_healthy=False,
                alternate_range_sensor_healthy=False,
            ),
            motion_enable=True,
        )
        self.assertEqual(AutonomyMode.HOLD, decision.mode)
        self.assertFalse(decision.motion_permitted)

    def test_invalid_localization_and_lost_fleet_connection_fail_safe(self) -> None:
        supervisor = AutonomySupervisor()
        localization = supervisor.evaluate(
            healthy(localization_valid=False),
            motion_enable=True,
        )
        disconnected = supervisor.evaluate(
            healthy(fleet_connected=False),
            motion_enable=True,
        )
        self.assertEqual(AutonomyMode.HOLD, localization.mode)
        self.assertEqual(AutonomyMode.RETURN_HOME, disconnected.mode)


if __name__ == "__main__":
    unittest.main()
