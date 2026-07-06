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

"""Static acceptance tests for deterministic simulation assets."""

import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def test_world_contains_required_runtime_systems() -> None:
    root = ET.parse(PACKAGE_ROOT / 'worlds' / 'factory.sdf').getroot()
    world = root.find("world[@name='amr_factory']")
    assert world is not None

    plugins = {plugin.attrib['name'] for plugin in world.findall('plugin')}
    assert {
        'gz::sim::systems::Physics',
        'gz::sim::systems::UserCommands',
        'gz::sim::systems::SceneBroadcaster',
        'gz::sim::systems::Imu',
        'gz::sim::systems::Sensors',
    } <= plugins


def test_world_contains_bounded_factory_and_stations() -> None:
    root = ET.parse(PACKAGE_ROOT / 'worlds' / 'factory.sdf').getroot()
    world = root.find("world[@name='amr_factory']")
    assert world is not None
    models = {model.attrib['name']: model for model in world.findall('model')}

    required_models = {
        'factory_floor',
        'north_wall',
        'south_wall',
        'east_wall',
        'west_wall',
        'central_rack',
        'pallet_obstacle',
        'station_infeed',
        'station_outfeed',
    }
    assert required_models <= models.keys()
    assert all(models[name].findtext('static') == 'true' for name in required_models)


def test_bridge_contract_covers_time_and_safety_relevant_sensors() -> None:
    with (PACKAGE_ROOT / 'config' / 'bridge.yaml').open(encoding='utf-8') as stream:
        bridges = yaml.safe_load(stream)

    by_topic = {entry['ros_topic_name']: entry for entry in bridges}
    assert {'/clock', '/scan', '/imu/data'} == by_topic.keys()
    assert all(entry['direction'] == 'GZ_TO_ROS' for entry in bridges)
    assert by_topic['/scan']['qos_profile'] == 'SENSOR_DATA'
    assert by_topic['/scan']['frame_id'] == 'lidar_link'
    assert by_topic['/imu/data']['frame_id'] == 'imu_link'
