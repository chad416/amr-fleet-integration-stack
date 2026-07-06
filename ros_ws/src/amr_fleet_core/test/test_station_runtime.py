"""End-to-end verification of MQTT station automation and pseudo-docking."""

import json
import unittest

from amr_fleet_core import MissionState, create_fleet_api
from amr_fleet_core.station_runtime import (
    MqttPlcStationSimulator,
    MqttStationCoordinator,
)
from test_api import mission_payload, robot_payload


class RecordingPublisher:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str, int, bool]] = []

    def publish(
        self,
        topic: str,
        payload: str,
        *,
        qos: int = 1,
        retain: bool = False,
    ) -> None:
        self.messages.append((topic, payload, qos, retain))


class StationRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.api = create_fleet_api(station_ids={"infeed"}, clock=lambda: 100.0)
        self.publisher = RecordingPublisher()
        self.coordinator = MqttStationCoordinator(
            self.api,
            self.publisher,
            ("infeed",),
        )
        self.plc = MqttPlcStationSimulator("infeed")
        initial_robot = robot_payload()
        initial_robot["pose"] = {"x": 1.0, "y": 0.0, "yaw": 0.0}
        self.api.update_robot(initial_robot)
        self.api.submit_mission(mission_payload("mqtt-runtime"))
        self.api.dispatch("mqtt-runtime", {})
        self.api.start("mqtt-runtime")
        self.api.arrive_at_station_approach("mqtt-runtime")
        self.api.request_station_access("mqtt-runtime", {})

    def test_correlated_mqtt_handshake_completes_pseudo_docking(self) -> None:
        self.coordinator.synchronize_leases(now=100.0)
        command_topic, command_payload, qos, retain = self.publisher.messages[-1]
        self.assertEqual(self.plc.command_topic, command_topic)
        self.assertEqual((1, False), (qos, retain))

        status_topic, status_payload = self.plc.handle_command(
            command_topic,
            command_payload,
            now=100.1,
        )
        result = self.coordinator.handle_status(
            status_topic,
            status_payload,
            received_at=100.1,
        )
        self.assertTrue(result.within_docking_tolerance)
        self.assertEqual(MissionState.COMPLETED, result.state)

        self.coordinator.synchronize_leases(now=100.2)
        release = json.loads(self.publisher.messages[-1][1])
        self.assertEqual("release", release["command"])

    def test_station_grant_does_not_move_robot_outside_docking_tolerance(self) -> None:
        far_robot = robot_payload()
        far_robot["pose"] = {"x": -5.0, "y": -5.0, "yaw": 0.0}
        far_robot["telemetry_at"] = 100.05
        self.api.update_robot(far_robot)
        self.coordinator.synchronize_leases(now=100.0)
        status = self.plc.handle_command(
            self.publisher.messages[-1][0],
            self.publisher.messages[-1][1],
            now=100.1,
        )
        result = self.coordinator.handle_status(*status, received_at=100.1)
        self.assertFalse(result.within_docking_tolerance)
        self.assertEqual(MissionState.AWAITING_STATION, result.state)


if __name__ == "__main__":
    unittest.main()
