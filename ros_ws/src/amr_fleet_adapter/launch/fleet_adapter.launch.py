"""Launch the AMR fleet adapter node."""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.substitutions import PathJoinSubstitution


def generate_launch_description() -> LaunchDescription:
    config = PathJoinSubstitution(
        [FindPackageShare("amr_fleet_adapter"), "config", "fleet_adapter.yaml"]
    )
    return LaunchDescription(
        [
            Node(
                package="amr_fleet_adapter",
                executable="fleet_adapter_node",
                name="amr_fleet_adapter",
                output="screen",
                parameters=[config],
            )
        ]
    )
