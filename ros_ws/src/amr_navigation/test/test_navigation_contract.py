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

"""Static contract tests for map and Nav2 integration."""

import importlib.util
from pathlib import Path
import sys

import yaml


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SIMULATION_ROOT = PACKAGE_ROOT.parent / 'amr_simulation'


class UniqueKeyLoader(yaml.SafeLoader):
    """YAML loader that rejects silently shadowed configuration keys."""


def construct_unique_mapping(loader, node, deep=False):
    """Construct one mapping and fail when a key is repeated."""
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                'while constructing a mapping',
                node.start_mark,
                f'duplicate key: {key}',
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    construct_unique_mapping,
)


def load_yaml(path: Path):
    """Load YAML while enforcing unique keys."""
    with path.open(encoding='utf-8') as stream:
        return yaml.load(stream, Loader=UniqueKeyLoader)


def load_generator():
    """Load the deterministic map generator from its installed-script source."""
    script = PACKAGE_ROOT / 'scripts' / 'generate_factory_map.py'
    specification = importlib.util.spec_from_file_location('generate_factory_map', script)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


def test_committed_factory_map_is_generated_from_world(tmp_path: Path) -> None:
    generator = load_generator()
    generator.render_map(SIMULATION_ROOT / 'worlds' / 'factory.sdf', tmp_path)

    assert (tmp_path / 'factory.pgm').read_bytes() == (
        PACKAGE_ROOT / 'maps' / 'factory.pgm'
    ).read_bytes()
    assert (tmp_path / 'factory.yaml').read_text(encoding='utf-8') == (
        PACKAGE_ROOT / 'maps' / 'factory.yaml'
    ).read_text(encoding='utf-8')


def test_navigation_frames_topics_and_safety_chain_are_consistent() -> None:
    params = load_yaml(PACKAGE_ROOT / 'config' / 'nav2_params.yaml')

    amcl = params['amcl']['ros__parameters']
    assert amcl['global_frame_id'] == 'map'
    assert amcl['odom_frame_id'] == 'odom'
    assert amcl['base_frame_id'] == 'base_footprint'
    assert amcl['scan_topic'] == '/scan'

    bt = params['bt_navigator']['ros__parameters']
    assert bt['odom_topic'] == '/base_controller/odom'

    smoother = params['velocity_smoother']['ros__parameters']
    monitor = params['collision_monitor']['ros__parameters']
    adapter = params['cmd_vel_adapter']['ros__parameters']
    assert smoother['odom_topic'] == '/base_controller/odom'
    assert monitor['cmd_vel_in_topic'] == 'cmd_vel_smoothed'
    assert monitor['cmd_vel_out_topic'] == adapter['input_topic']
    assert adapter['output_topic'] == '/base_controller/cmd_vel'
    assert adapter['max_linear_x'] == 0.80
    assert adapter['max_angular_z'] == 1.40
    assert {'stop_zone', 'slowdown_zone'} <= set(monitor['polygons'])


def test_navigation_launch_rewrites_map_server_yaml_filename() -> None:
    launch_text = (PACKAGE_ROOT / 'launch' / 'navigation.launch.py').read_text(
        encoding='utf-8'
    )

    assert 'RewrittenYaml' in launch_text
    assert "param_rewrites={'yaml_filename': map_file}" in launch_text
    assert 'parameters=[configured_params]' in launch_text


def test_named_waypoints_are_inside_map_bounds() -> None:
    map_metadata = load_yaml(PACKAGE_ROOT / 'maps' / 'factory.yaml')
    waypoint_config = load_yaml(PACKAGE_ROOT / 'config' / 'waypoints.yaml')
    acceptance_source = (
        PACKAGE_ROOT / 'scripts' / 'navigation_acceptance.py'
    ).read_text(encoding='utf-8')

    inspection_west = waypoint_config['waypoints']['inspection_west']
    assert f"default={inspection_west['x']}" in acceptance_source
    assert f"default={inspection_west['y']}" in acceptance_source

    origin_x, origin_y, _ = map_metadata['origin']
    resolution = map_metadata['resolution']
    pgm = (PACKAGE_ROOT / 'maps' / 'factory.pgm').read_bytes()
    header, width_height, _, pixels = pgm.split(b'\n', 3)
    width, height = (int(value) for value in width_height.split())
    assert header == b'P5'

    for name, pose in waypoint_config['waypoints'].items():
        image_x = int((pose['x'] - origin_x) / resolution)
        image_y = height - 1 - int((pose['y'] - origin_y) / resolution)
        assert 0 <= image_x < width and 0 <= image_y < height, name
        assert pixels[image_y * width + image_x] == 254, name
