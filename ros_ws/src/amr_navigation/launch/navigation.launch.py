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

"""Launch Gazebo, AMCL and the complete Nav2 stack against the factory map."""

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    GroupAction,
    IncludeLaunchDescription,
    SetEnvironmentVariable,
    TimerAction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, SetParameter
from launch_ros.descriptions import ParameterFile
from nav2_common.launch import RewrittenYaml


def generate_launch_description() -> LaunchDescription:
    navigation_share = Path(get_package_share_directory('amr_navigation'))
    simulation_share = Path(get_package_share_directory('amr_simulation'))

    headless = LaunchConfiguration('headless')
    map_file = LaunchConfiguration('map')
    params_file = LaunchConfiguration('params_file')
    configured_params = ParameterFile(
        RewrittenYaml(
            source_file=params_file,
            param_rewrites={'yaml_filename': map_file},
            convert_types=True,
        ),
        allow_substs=True,
    )

    simulation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            str(simulation_share / 'launch' / 'simulation.launch.py')
        ),
        launch_arguments={'headless': headless}.items(),
    )

    common_arguments = ['--ros-args', '--log-level', 'info']
    transform_remappings = [('/tf', 'tf'), ('/tf_static', 'tf_static')]

    localization_nodes = GroupAction(
        actions=[
            SetParameter('use_sim_time', True),
            Node(
                package='nav2_map_server',
                executable='map_server',
                name='map_server',
                output='screen',
                parameters=[configured_params],
                arguments=common_arguments,
                remappings=transform_remappings,
            ),
            Node(
                package='nav2_amcl',
                executable='amcl',
                name='amcl',
                output='screen',
                parameters=[configured_params],
                arguments=common_arguments,
                remappings=transform_remappings,
            ),
            Node(
                package='nav2_lifecycle_manager',
                executable='lifecycle_manager',
                name='lifecycle_manager_localization',
                output='screen',
                arguments=common_arguments,
                parameters=[
                    {
                        'autostart': True,
                        'node_names': ['map_server', 'amcl'],
                    }
                ],
            ),
        ]
    )

    navigation_nodes = GroupAction(
        actions=[
            SetParameter('use_sim_time', True),
            Node(
                package='nav2_controller',
                executable='controller_server',
                name='controller_server',
                output='screen',
                parameters=[configured_params],
                arguments=common_arguments,
                remappings=transform_remappings + [('cmd_vel', 'cmd_vel_nav')],
            ),
            Node(
                package='nav2_smoother',
                executable='smoother_server',
                name='smoother_server',
                output='screen',
                parameters=[configured_params],
                arguments=common_arguments,
                remappings=transform_remappings,
            ),
            Node(
                package='nav2_planner',
                executable='planner_server',
                name='planner_server',
                output='screen',
                parameters=[configured_params],
                arguments=common_arguments,
                remappings=transform_remappings,
            ),
            Node(
                package='nav2_behaviors',
                executable='behavior_server',
                name='behavior_server',
                output='screen',
                parameters=[configured_params],
                arguments=common_arguments,
                remappings=transform_remappings + [('cmd_vel', 'cmd_vel_nav')],
            ),
            Node(
                package='nav2_bt_navigator',
                executable='bt_navigator',
                name='bt_navigator',
                output='screen',
                parameters=[configured_params],
                arguments=common_arguments,
                remappings=transform_remappings,
            ),
            Node(
                package='nav2_waypoint_follower',
                executable='waypoint_follower',
                name='waypoint_follower',
                output='screen',
                parameters=[configured_params],
                arguments=common_arguments,
                remappings=transform_remappings,
            ),
            Node(
                package='nav2_velocity_smoother',
                executable='velocity_smoother',
                name='velocity_smoother',
                output='screen',
                parameters=[configured_params],
                arguments=common_arguments,
                remappings=transform_remappings + [('cmd_vel', 'cmd_vel_nav')],
            ),
            Node(
                package='nav2_collision_monitor',
                executable='collision_monitor',
                name='collision_monitor',
                output='screen',
                parameters=[configured_params],
                arguments=common_arguments,
                remappings=transform_remappings,
            ),
            Node(
                package='amr_navigation',
                executable='cmd_vel_adapter.py',
                name='cmd_vel_adapter',
                output='screen',
                parameters=[{'use_sim_time': True}],
                arguments=common_arguments,
            ),
            Node(
                package='amr_navigation',
                executable='autonomy_supervisor.py',
                name='autonomy_supervisor',
                output='screen',
                parameters=[{'use_sim_time': True}],
                arguments=common_arguments,
            ),
            Node(
                package='nav2_lifecycle_manager',
                executable='lifecycle_manager',
                name='lifecycle_manager_navigation',
                output='screen',
                arguments=common_arguments,
                parameters=[
                    {
                        'autostart': True,
                        'node_names': [
                            'controller_server',
                            'smoother_server',
                            'planner_server',
                            'behavior_server',
                            'velocity_smoother',
                            'collision_monitor',
                            'bt_navigator',
                            'waypoint_follower',
                        ],
                    }
                ],
            ),
        ]
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument('headless', default_value='false'),
            DeclareLaunchArgument(
                'map',
                default_value=str(navigation_share / 'maps' / 'factory.yaml'),
                description='Versioned Nav2 map metadata file.',
            ),
            DeclareLaunchArgument(
                'params_file',
                default_value=str(navigation_share / 'config' / 'nav2_params.yaml'),
                description='Nav2 parameter file.',
            ),
            SetEnvironmentVariable('RCUTILS_LOGGING_BUFFERED_STREAM', '1'),
            simulation,
            TimerAction(period=5.0, actions=[localization_nodes, navigation_nodes]),
        ]
    )
