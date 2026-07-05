"""Verification of the mission lifecycle aggregate."""

import unittest

from amr_fleet_core import InvalidTransition, Mission, MissionState, MissionStop, Pose2D


def stop(station_id: str, x: float) -> MissionStop:
    return MissionStop(station_id, f"{station_id}_approach", Pose2D(x, 0.0))


class MissionTests(unittest.TestCase):
    def test_nominal_two_stop_mission(self) -> None:
        mission = Mission("mission-001", (stop("infeed", 1.0), stop("outfeed", 5.0)))

        mission.assign("amr-01")
        mission.start()
        mission.arrive_at_station_approach()
        mission.grant_station_access("lease-1")
        mission.start_docking("lease-1")
        mission.confirm_docked("lease-1")
        mission.complete_transfer("lease-1")

        self.assertEqual(mission.state, MissionState.NAVIGATING)
        self.assertEqual(mission.current_stop_index, 1)
        self.assertIsNone(mission.station_lease_id)

        mission.arrive_at_station_approach()
        mission.grant_station_access("lease-2")
        mission.start_docking("lease-2")
        mission.confirm_docked("lease-2")
        mission.complete_transfer("lease-2")

        self.assertEqual(mission.state, MissionState.COMPLETED)
        self.assertTrue(mission.state.terminal)
        self.assertEqual(
            [event.sequence for event in mission.events], list(range(mission.revision + 1))
        )

    def test_docking_requires_correlated_station_lease(self) -> None:
        mission = Mission("mission-002", (stop("infeed", 1.0),))
        mission.assign("amr-01")
        mission.start()
        mission.arrive_at_station_approach()

        with self.assertRaises(InvalidTransition):
            mission.start_docking("lease-not-granted")

        mission.grant_station_access("lease-correct")
        with self.assertRaises(InvalidTransition):
            mission.start_docking("lease-stale")

    def test_pause_and_resume_restore_previous_phase(self) -> None:
        mission = Mission("mission-003", (stop("infeed", 1.0),))
        mission.assign("amr-01")
        mission.start()
        mission.arrive_at_station_approach()
        mission.pause()

        self.assertEqual(mission.state, MissionState.PAUSED)
        mission.resume()
        self.assertEqual(mission.state, MissionState.AWAITING_STATION)

    def test_terminal_state_cannot_be_reopened(self) -> None:
        mission = Mission("mission-004", (stop("infeed", 1.0),))
        mission.cancel("operator canceled before dispatch")

        with self.assertRaises(InvalidTransition):
            mission.assign("amr-01")
        with self.assertRaises(InvalidTransition):
            mission.cancel("duplicate cancel")


if __name__ == "__main__":
    unittest.main()
