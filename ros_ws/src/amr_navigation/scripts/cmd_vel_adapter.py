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

"""Validate, constrain and stamp Jazzy Nav2 velocity commands."""

from math import isfinite

try:
    from geometry_msgs.msg import Twist, TwistStamped
    import rclpy
    from rclpy.executors import ExternalShutdownException
    from rclpy.node import Node

    ROS_AVAILABLE = True
except ModuleNotFoundError:
    # Keep the pure command-boundary function importable on a non-ROS host.
    # The executable node itself remains available only in the ROS runtime.
    ROS_AVAILABLE = False


def clamp(value: float, minimum: float, maximum: float) -> float:
    """Constrain a scalar to inclusive limits."""
    return min(maximum, max(minimum, value))


def sanitize_command(
    linear_x: float,
    linear_y: float,
    angular_z: float,
    min_linear_x: float,
    max_linear_x: float,
    max_angular_z: float,
) -> tuple[float, float]:
    """Reject non-finite input and apply differential-drive limits."""
    if not all(isfinite(value) for value in (linear_x, linear_y, angular_z)):
        return 0.0, 0.0
    return (
        clamp(linear_x, min_linear_x, max_linear_x),
        clamp(angular_z, -max_angular_z, max_angular_z),
    )


if ROS_AVAILABLE:

    class CommandVelocityAdapter(Node):
        """Bridge Nav2 Twist commands to the controller's TwistStamped API."""

        def __init__(self) -> None:
            super().__init__('cmd_vel_adapter')
            self.declare_parameter('input_topic', '/cmd_vel_safe')
            self.declare_parameter('output_topic', '/base_controller/cmd_vel')
            self.declare_parameter('frame_id', 'base_link')
            self.declare_parameter('min_linear_x', -0.35)
            self.declare_parameter('max_linear_x', 0.80)
            self.declare_parameter('max_angular_z', 1.40)

            input_topic = self.get_parameter('input_topic').value
            output_topic = self.get_parameter('output_topic').value
            self.frame_id = self.get_parameter('frame_id').value
            self.min_linear_x = float(self.get_parameter('min_linear_x').value)
            self.max_linear_x = float(self.get_parameter('max_linear_x').value)
            self.max_angular_z = float(self.get_parameter('max_angular_z').value)

            self.publisher = self.create_publisher(TwistStamped, output_topic, 10)
            self.subscription = self.create_subscription(Twist, input_topic, self.forward, 10)

        def forward(self, command: Twist) -> None:
            """Publish a finite, non-holonomic and constrained stamped command."""
            requested = (command.linear.x, command.linear.y, command.angular.z)
            linear_x, angular_z = sanitize_command(
                *requested,
                self.min_linear_x,
                self.max_linear_x,
                self.max_angular_z,
            )
            if not all(isfinite(value) for value in requested):
                self.get_logger().error('Rejected non-finite velocity command')

            output = TwistStamped()
            output.header.stamp = self.get_clock().now().to_msg()
            output.header.frame_id = self.frame_id
            output.twist.linear.x = linear_x
            output.twist.angular.z = angular_z
            self.publisher.publish(output)


    def main() -> None:
        """Run the command adapter node."""
        rclpy.init()
        node = CommandVelocityAdapter()
        try:
            rclpy.spin(node)
        except (ExternalShutdownException, KeyboardInterrupt):
            pass
        finally:
            node.destroy_node()
            if rclpy.ok():
                rclpy.shutdown()

else:

    def main() -> None:
        """Explain why the ROS executable cannot run on a non-ROS host."""
        raise RuntimeError(
            'cmd_vel_adapter requires a sourced ROS 2 environment; '
            'sanitize_command is available for host-side verification'
        )


if __name__ == '__main__':
    main()
