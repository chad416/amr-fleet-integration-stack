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

"""Launch Gazebo with lifecycle-managed asynchronous SLAM and map saving."""

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    navigation_share = Path(get_package_share_directory('amr_navigation'))
    simulation_share = Path(get_package_share_directory('amr_simulation'))
    slam_share = Path(get_package_share_directory('slam_toolbox'))

    headless = LaunchConfiguration('headless')
    slam_params = LaunchConfiguration('slam_params_file')

    simulation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(simulation_share / 'launch' / 'simulation.launch.py')),
        launch_arguments={'headless': headless}.items(),
    )
    slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(slam_share / 'launch' / 'online_async_launch.py')),
        launch_arguments={
            'use_sim_time': 'true',
            'autostart': 'true',
            'use_lifecycle_manager': 'false',
            'slam_params_file': slam_params,
        }.items(),
    )
    map_saver = Node(
        package='nav2_map_server',
        executable='map_saver_server',
        name='map_saver',
        output='screen',
        parameters=[slam_params, {'use_sim_time': True}],
    )
    map_saver_lifecycle = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_mapping',
        output='screen',
        parameters=[{'autostart': True, 'node_names': ['map_saver']}],
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument('headless', default_value='false'),
            DeclareLaunchArgument(
                'slam_params_file',
                default_value=str(navigation_share / 'config' / 'slam_toolbox.yaml'),
            ),
            simulation,
            TimerAction(period=5.0, actions=[slam, map_saver, map_saver_lifecycle]),
        ]
    )
