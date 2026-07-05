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

"""Semantic contract tests for the generated AMR description."""

from math import isclose
from pathlib import Path
import xml.etree.ElementTree as ET

import xacro
import yaml


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def generated_robot() -> ET.Element:
    """Expand Xacro and return the generated URDF root."""
    document = xacro.process_file(str(PACKAGE_ROOT / 'urdf' / 'amr.urdf.xacro'))
    return ET.fromstring(document.toxml())


def test_xacro_expands_to_expected_robot_graph() -> None:
    robot = generated_robot()
    assert robot.attrib['name'] == 'portfolio_amr'

    links = {link.attrib['name'] for link in robot.findall('link')}
    joints = {joint.attrib['name'] for joint in robot.findall('joint')}
    assert {
        'base_footprint',
        'base_link',
        'left_wheel_link',
        'right_wheel_link',
        'lidar_link',
        'imu_link',
    } <= links
    assert {'left_wheel_joint', 'right_wheel_joint', 'lidar_joint', 'imu_joint'} <= joints


def test_controller_geometry_matches_generated_model() -> None:
    robot = generated_robot()
    joints = {joint.attrib['name']: joint for joint in robot.findall('joint')}
    left_y = float(joints['left_wheel_joint'].find('origin').attrib['xyz'].split()[1])
    right_y = float(joints['right_wheel_joint'].find('origin').attrib['xyz'].split()[1])
    separation = abs(left_y - right_y)

    wheel_link = robot.find("link[@name='left_wheel_link']")
    assert wheel_link is not None
    radius = float(wheel_link.find('collision/geometry/cylinder').attrib['radius'])

    with (PACKAGE_ROOT / 'config' / 'controllers.yaml').open(encoding='utf-8') as stream:
        controller_config = yaml.safe_load(stream)['base_controller']['ros__parameters']

    assert isclose(separation, controller_config['wheel_separation'], abs_tol=1e-9)
    assert isclose(radius, controller_config['wheel_radius'], abs_tol=1e-9)


def test_simulation_plugins_and_sensor_topics_are_declared() -> None:
    robot = generated_robot()
    plugins = robot.findall('gazebo/plugin')
    assert any(plugin.attrib['filename'] == 'gz_ros2_control-system' for plugin in plugins)

    sensors = robot.findall('gazebo/sensor')
    topics = {sensor.findtext('topic') for sensor in sensors}
    assert {'scan', 'imu/data'} <= topics

    control = robot.find("ros2_control[@name='GazeboSystem']")
    assert control is not None
    controlled_joints = {joint.attrib['name'] for joint in control.findall('joint')}
    assert controlled_joints == {'left_wheel_joint', 'right_wheel_joint'}
