#!/usr/bin/env python3
# Copyright 2026 AMR Fleet Integration Stack Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""ROS 2 adapter for fail-safe autonomy health supervision."""

from __future__ import annotations

from collections.abc import Callable

import rclpy
from amr_fleet_core import AutonomyHealth, AutonomySupervisor, MotionEnableInterlock
from rclpy.node import Node
from std_msgs.msg import Bool, String


class AutonomySupervisorNode(Node):
    def __init__(self) -> None:
        super().__init__("autonomy_supervisor")
        self._health = {
            "localization_valid": False,
            "primary_range_sensor_healthy": False,
            "alternate_range_sensor_healthy": False,
            "fleet_connected": False,
            "home_route_available": False,
            "emergency_stop_active": False,
        }
        self._interlock = MotionEnableInterlock()
        self._supervisor = AutonomySupervisor()
        self._mode_publisher = self.create_publisher(String, "autonomy/mode", 10)
        self._motion_publisher = self.create_publisher(Bool, "autonomy/motion_permitted", 10)
        self._subscribe("localization/valid", self._setter("localization_valid"))
        self._subscribe(
            "sensors/primary_range_healthy",
            self._setter("primary_range_sensor_healthy"),
        )
        self._subscribe(
            "sensors/alternate_range_healthy",
            self._setter("alternate_range_sensor_healthy"),
        )
        self._subscribe("fleet/connected", self._setter("fleet_connected"))
        self._subscribe(
            "navigation/home_route_available",
            self._setter("home_route_available"),
        )
        self._subscribe("safety/emergency_stop", self._on_emergency_stop)
        self._subscribe("operator/start", self._on_operator_start)
        self.create_timer(0.1, self._publish_decision)

    def _subscribe(self, topic: str, callback: Callable[[Bool], None]) -> None:
        self.create_subscription(Bool, topic, callback, 10)

    def _setter(self, field: str) -> Callable[[Bool], None]:
        def update(message: Bool) -> None:
            self._health[field] = bool(message.data)

        return update

    def _on_emergency_stop(self, message: Bool) -> None:
        active = bool(message.data)
        self._health["emergency_stop_active"] = active
        self._interlock.set_emergency_stop(active)

    def _on_operator_start(self, message: Bool) -> None:
        if not message.data:
            return
        try:
            self._interlock.operator_start()
        except RuntimeError as error:
            self.get_logger().warning(str(error))

    def _publish_decision(self) -> None:
        decision = self._supervisor.evaluate(
            AutonomyHealth(**self._health),
            motion_enable=self._interlock.motion_permitted,
        )
        mode = String()
        mode.data = decision.mode.value
        motion = Bool()
        motion.data = decision.motion_permitted
        self._mode_publisher.publish(mode)
        self._motion_publisher.publish(motion)


def main() -> None:
    rclpy.init()
    node = AutonomySupervisorNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
