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

"""Send a deterministic Nav2 goal and fail unless it succeeds."""

import argparse
from math import cos, sin
import sys  # noqa: I100 - Ruff owns repository import ordering.

from action_msgs.msg import GoalStatus
from nav2_msgs.action import NavigateToPose
import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.parameter import Parameter


class NavigationAcceptance(Node):
    """Minimal action client used by the headless acceptance gate."""

    def __init__(self) -> None:
        super().__init__(
            'navigation_acceptance',
            parameter_overrides=[Parameter('use_sim_time', value=True)],
            automatically_declare_parameters_from_overrides=True,
        )
        self.client = ActionClient(self, NavigateToPose, '/navigate_to_pose')

    def navigate(self, x: float, y: float, yaw: float) -> bool:
        """Navigate to a map pose and return whether Nav2 reports success."""
        if not self.client.wait_for_server(timeout_sec=120.0):
            self.get_logger().error('NavigateToPose action server did not become ready')
            return False

        goal = NavigateToPose.Goal()
        goal.pose.header.frame_id = 'map'
        goal.pose.header.stamp = self.get_clock().now().to_msg()
        goal.pose.pose.position.x = x
        goal.pose.pose.position.y = y
        goal.pose.pose.orientation.z = sin(yaw / 2.0)
        goal.pose.pose.orientation.w = cos(yaw / 2.0)

        send_future = self.client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, send_future, timeout_sec=30.0)
        if not send_future.done() or send_future.result() is None:
            self.get_logger().error('Timed out submitting navigation goal')
            return False
        goal_handle = send_future.result()
        if not goal_handle.accepted:
            self.get_logger().error('Navigation goal was rejected')
            return False

        self.get_logger().info(f'Goal accepted: x={x:.2f}, y={y:.2f}, yaw={yaw:.2f}')
        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future, timeout_sec=180.0)
        if not result_future.done() or result_future.result() is None:
            self.get_logger().error('Navigation goal timed out')
            return False

        status = result_future.result().status
        if status != GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().error(f'Navigation failed with action status {status}')
            return False
        self.get_logger().info('Navigation goal succeeded')
        return True


def main() -> int:
    """Run the acceptance action client."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--x', type=float, default=-2.4)
    parser.add_argument('--y', type=float, default=-1.5)
    parser.add_argument('--yaw', type=float, default=0.0)
    arguments, ros_arguments = parser.parse_known_args()

    rclpy.init(args=ros_arguments)
    node = NavigationAcceptance()
    try:
        return 0 if node.navigate(arguments.x, arguments.y, arguments.yaw) else 1
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    sys.exit(main())
