# Copyright 2026 AMR Fleet Integration Stack Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

"""Launch a two-AMR Gazebo simulation scaffold with namespace isolation."""

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    GroupAction,
    IncludeLaunchDescription,
    RegisterEventHandler,
)
from launch.conditions import IfCondition, UnlessCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node, PushRosNamespace
from launch_ros.parameter_descriptions import ParameterValue

ROBOTS = (
    {
        "namespace": "amr_01",
        "entity_name": "amr_01",
        "frame_prefix": "amr_01/",
        "spawn_x": "-3.5",
        "spawn_y": "0.8",
        "spawn_z": "0.03",
        "spawn_yaw": "0.0",
    },
    {
        "namespace": "amr_02",
        "entity_name": "amr_02",
        "frame_prefix": "amr_02/",
        "spawn_x": "-3.5",
        "spawn_y": "-0.8",
        "spawn_z": "0.03",
        "spawn_yaw": "0.0",
    },
)


def generate_launch_description() -> LaunchDescription:
    description_share = Path(get_package_share_directory("amr_description"))
    simulation_share = Path(get_package_share_directory("amr_simulation"))
    ros_gz_share = Path(get_package_share_directory("ros_gz_sim"))

    xacro_file = description_share / "urdf" / "amr.urdf.xacro"
    default_world = simulation_share / "worlds" / "factory.sdf"
    bridge_config = simulation_share / "config" / "multi_robot_bridge.yaml"
    gz_launch = ros_gz_share / "launch" / "gz_sim.launch.py"

    headless = LaunchConfiguration("headless")
    world = LaunchConfiguration("world")
    actions = [
        DeclareLaunchArgument(
            "headless",
            default_value="false",
            description="Run the Gazebo server without its graphical client.",
        ),
        DeclareLaunchArgument(
            "world",
            default_value=str(default_world),
            description="Absolute path to an SDF world.",
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(gz_launch)),
            launch_arguments={"gz_args": ["-r -s ", world]}.items(),
            condition=IfCondition(headless),
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(gz_launch)),
            launch_arguments={"gz_args": ["-r ", world]}.items(),
            condition=UnlessCondition(headless),
        ),
        Node(
            package="ros_gz_bridge",
            executable="bridge_node",
            name="ros_gz_bridge",
            output="screen",
            parameters=[{"config_file": str(bridge_config)}],
        ),
    ]

    for robot in ROBOTS:
        robot_description = ParameterValue(
            Command(
                [
                    "xacro ",
                    str(xacro_file),
                    " namespace:=",
                    robot["namespace"],
                ]
            ),
            value_type=str,
        )
        actions.append(_robot_group(robot, robot_description))

    return LaunchDescription(actions)


def _robot_group(robot: dict[str, str], robot_description: ParameterValue) -> GroupAction:
    namespace = robot["namespace"]
    spawn_robot = Node(
        package="ros_gz_sim",
        executable="create",
        name=f"spawn_{namespace}",
        output="screen",
        parameters=[
            {
                "world": "amr_factory",
                "topic": f"/{namespace}/robot_description",
                "name": robot["entity_name"],
                "allow_renaming": False,
                "x": robot["spawn_x"],
                "y": robot["spawn_y"],
                "z": robot["spawn_z"],
                "Y": robot["spawn_yaw"],
            }
        ],
    )
    controller_manager = f"/{namespace}/controller_manager"
    joint_state_spawner = Node(
        package="controller_manager",
        executable="spawner",
        name="joint_state_spawner",
        arguments=[
            "joint_state_broadcaster",
            "--controller-manager",
            controller_manager,
            "--controller-manager-timeout",
            "60",
        ],
        output="screen",
    )
    base_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        name="base_controller_spawner",
        arguments=[
            "base_controller",
            "--controller-manager",
            controller_manager,
            "--controller-manager-timeout",
            "60",
        ],
        output="screen",
    )
    return GroupAction(
        [
            PushRosNamespace(namespace),
            Node(
                package="robot_state_publisher",
                executable="robot_state_publisher",
                name="robot_state_publisher",
                output="screen",
                parameters=[
                    {
                        "robot_description": robot_description,
                        "frame_prefix": robot["frame_prefix"],
                        "use_sim_time": True,
                    }
                ],
            ),
            spawn_robot,
            RegisterEventHandler(
                OnProcessExit(target_action=spawn_robot, on_exit=[joint_state_spawner])
            ),
            RegisterEventHandler(
                OnProcessExit(
                    target_action=joint_state_spawner,
                    on_exit=[base_controller_spawner],
                )
            ),
        ]
    )
