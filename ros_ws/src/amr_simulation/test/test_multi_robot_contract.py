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

"""Static acceptance tests for the multi-robot simulation scaffold."""

import ast
from pathlib import Path

import yaml

PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def test_multi_robot_config_has_unique_namespaces_entities_and_frame_prefixes() -> None:
    with (PACKAGE_ROOT / 'config' / 'multi_robot_fleet.yaml').open(encoding='utf-8') as stream:
        config = yaml.safe_load(stream)

    robots = config['robots']
    assert len(robots) >= 2
    assert len({robot['id'] for robot in robots}) == len(robots)
    assert len({robot['namespace'] for robot in robots}) == len(robots)
    assert len({robot['entity_name'] for robot in robots}) == len(robots)
    assert len({robot['frame_prefix'] for robot in robots}) == len(robots)
    assert all(robot['namespace'].startswith('/') for robot in robots)
    assert all(robot['frame_prefix'].endswith('/') for robot in robots)


def test_multi_robot_spawn_poses_are_separated() -> None:
    with (PACKAGE_ROOT / 'config' / 'multi_robot_fleet.yaml').open(encoding='utf-8') as stream:
        config = yaml.safe_load(stream)

    poses = [
        (robot['spawn']['x'], robot['spawn']['y'], robot['spawn']['yaw'])
        for robot in config['robots']
    ]
    assert len(set(poses)) == len(poses)
    assert abs(poses[0][1] - poses[1][1]) >= 1.0


def test_multi_robot_launch_uses_namespaced_robot_description_topics() -> None:
    launch_text = (PACKAGE_ROOT / 'launch' / 'multi_robot_simulation.launch.py').read_text(
        encoding='utf-8'
    )

    assert 'PushRosNamespace(namespace)' in launch_text
    assert 'frame_prefix' in launch_text
    assert '/{namespace}/robot_description' in launch_text
    assert 'allow_renaming' in launch_text
    assert 'controller_manager' in launch_text
    assert 'joint_state_broadcaster' in launch_text
    assert 'base_controller' in launch_text


def test_multi_robot_launch_passes_numeric_spawn_parameters() -> None:
    launch_path = PACKAGE_ROOT / 'launch' / 'multi_robot_simulation.launch.py'
    tree = ast.parse(launch_path.read_text(encoding='utf-8'))
    robots_assignment = next(
        node
        for node in tree.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == 'ROBOTS'
    )
    robots = ast.literal_eval(robots_assignment.value)

    for robot in robots:
        for parameter in ('spawn_x', 'spawn_y', 'spawn_z', 'spawn_yaw'):
            assert isinstance(robot[parameter], float)


def test_multi_robot_bridge_isolates_sensor_topics_and_frames() -> None:
    with (PACKAGE_ROOT / 'config' / 'multi_robot_bridge.yaml').open(encoding='utf-8') as stream:
        bridges = yaml.safe_load(stream)

    topics = {entry['ros_topic_name'] for entry in bridges}
    assert {
        '/clock',
        '/amr_01/scan',
        '/amr_01/imu/data',
        '/amr_02/scan',
        '/amr_02/imu/data',
    } == topics
    frames = {entry.get('frame_id') for entry in bridges if 'frame_id' in entry}
    assert frames == {
        'amr_01/lidar_link',
        'amr_01/imu_link',
        'amr_02/lidar_link',
        'amr_02/imu_link',
    }
