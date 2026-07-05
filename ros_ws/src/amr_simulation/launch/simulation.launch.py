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

"""Launch the complete single-AMR Gazebo simulation baseline."""

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.actions import RegisterEventHandler
from launch.conditions import IfCondition, UnlessCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description() -> LaunchDescription:
    description_share = Path(get_package_share_directory('amr_description'))
    simulation_share = Path(get_package_share_directory('amr_simulation'))
    ros_gz_share = Path(get_package_share_directory('ros_gz_sim'))

    xacro_file = description_share / 'urdf' / 'amr.urdf.xacro'
    default_world = simulation_share / 'worlds' / 'factory.sdf'
    bridge_config = simulation_share / 'config' / 'bridge.yaml'
    gz_launch = ros_gz_share / 'launch' / 'gz_sim.launch.py'

    headless = LaunchConfiguration('headless')
    world = LaunchConfiguration('world')
    robot_name = LaunchConfiguration('robot_name')
    spawn_x = LaunchConfiguration('spawn_x')
    spawn_y = LaunchConfiguration('spawn_y')
    spawn_z = LaunchConfiguration('spawn_z')
    spawn_yaw = LaunchConfiguration('spawn_yaw')

    robot_description = ParameterValue(
        Command(['xacro ', str(xacro_file)]),
        value_type=str,
    )

    gazebo_headless = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(gz_launch)),
        launch_arguments={'gz_args': ['-r -s ', world]}.items(),
        condition=IfCondition(headless),
    )
    gazebo_gui = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(gz_launch)),
        launch_arguments={'gz_args': ['-r ', world]}.items(),
        condition=UnlessCondition(headless),
    )

    state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[
            {
                'robot_description': robot_description,
                'use_sim_time': True,
            }
        ],
    )

    bridge = Node(
        package='ros_gz_bridge',
        executable='bridge_node',
        name='ros_gz_bridge',
        output='screen',
        parameters=[{'config_file': str(bridge_config)}],
    )

    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        name='spawn_amr',
        output='screen',
        parameters=[
            {
                'world': 'amr_factory',
                'topic': 'robot_description',
                'name': robot_name,
                'allow_renaming': False,
                'x': spawn_x,
                'y': spawn_y,
                'z': spawn_z,
                'Y': spawn_yaw,
            }
        ],
    )

    joint_state_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=[
            'joint_state_broadcaster',
            '--controller-manager',
            '/controller_manager',
            '--controller-manager-timeout',
            '60',
            '--service-call-timeout',
            '10',
        ],
        output='screen',
    )
    base_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=[
            'base_controller',
            '--controller-manager',
            '/controller_manager',
            '--controller-manager-timeout',
            '60',
            '--service-call-timeout',
            '10',
        ],
        output='screen',
    )

    start_joint_state_after_spawn = RegisterEventHandler(
        OnProcessExit(
            target_action=spawn_robot,
            on_exit=[joint_state_spawner],
        )
    )
    start_base_after_joint_state = RegisterEventHandler(
        OnProcessExit(
            target_action=joint_state_spawner,
            on_exit=[base_controller_spawner],
        )
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                'headless',
                default_value='false',
                description='Run the Gazebo server without its graphical client.',
            ),
            DeclareLaunchArgument(
                'world',
                default_value=str(default_world),
                description='Absolute path to an SDF world.',
            ),
            DeclareLaunchArgument('robot_name', default_value='portfolio_amr'),
            DeclareLaunchArgument('spawn_x', default_value='-3.5'),
            DeclareLaunchArgument('spawn_y', default_value='0.0'),
            DeclareLaunchArgument('spawn_z', default_value='0.03'),
            DeclareLaunchArgument('spawn_yaw', default_value='0.0'),
            gazebo_headless,
            gazebo_gui,
            state_publisher,
            bridge,
            spawn_robot,
            start_joint_state_after_spawn,
            start_base_after_joint_state,
        ]
    )
