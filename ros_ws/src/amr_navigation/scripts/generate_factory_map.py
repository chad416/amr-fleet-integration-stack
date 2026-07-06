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

"""Rasterize static Gazebo collision boxes into a deterministic Nav2 map."""

import argparse
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from math import cos, sin
from pathlib import Path


@dataclass(frozen=True)
class Box:
    """A 2D projection of an SDF collision box."""

    x: float
    y: float
    yaw: float
    size_x: float
    size_y: float

    def contains(self, point_x: float, point_y: float) -> bool:
        """Return whether a world point lies inside the oriented box."""
        delta_x = point_x - self.x
        delta_y = point_y - self.y
        local_x = cos(self.yaw) * delta_x + sin(self.yaw) * delta_y
        local_y = -sin(self.yaw) * delta_x + cos(self.yaw) * delta_y
        return abs(local_x) <= self.size_x / 2 and abs(local_y) <= self.size_y / 2


def pose_values(element: ET.Element | None) -> tuple[float, float, float]:
    """Extract x, y and yaw from an optional SDF pose element."""
    values = [float(value) for value in (element.text if element is not None else '').split()]
    values.extend([0.0] * (6 - len(values)))
    return values[0], values[1], values[5]


def world_geometry(world_path: Path) -> tuple[float, float, float, float, list[Box]]:
    """Read map bounds and obstacle boxes from the factory SDF."""
    root = ET.parse(world_path).getroot()
    world = root.find("world[@name='amr_factory']")
    if world is None:
        raise ValueError('SDF does not contain world amr_factory')

    floor = world.find("model[@name='factory_floor']")
    if floor is None:
        raise ValueError('factory_floor model is required to define map bounds')
    floor_size = floor.findtext('link/collision/geometry/box/size')
    if floor_size is None:
        raise ValueError('factory_floor must contain a box collision')
    floor_x, floor_y, _ = (float(value) for value in floor_size.split())
    floor_pose_x, floor_pose_y, _ = pose_values(floor.find('pose'))
    min_x = floor_pose_x - floor_x / 2
    min_y = floor_pose_y - floor_y / 2

    boxes: list[Box] = []
    for model in world.findall('model'):
        if model.attrib.get('name') == 'factory_floor' or model.findtext('static') != 'true':
            continue
        model_x, model_y, model_yaw = pose_values(model.find('pose'))
        for collision in model.findall('link/collision'):
            size_text = collision.findtext('geometry/box/size')
            if size_text is None:
                continue
            size_x, size_y, _ = (float(value) for value in size_text.split())
            collision_x, collision_y, collision_yaw = pose_values(collision.find('pose'))
            rotated_x = cos(model_yaw) * collision_x - sin(model_yaw) * collision_y
            rotated_y = sin(model_yaw) * collision_x + cos(model_yaw) * collision_y
            boxes.append(
                Box(
                    x=model_x + rotated_x,
                    y=model_y + rotated_y,
                    yaw=model_yaw + collision_yaw,
                    size_x=size_x,
                    size_y=size_y,
                )
            )
    return min_x, min_y, floor_x, floor_y, boxes


def render_map(world_path: Path, output_dir: Path, resolution: float = 0.05) -> None:
    """Write a PGM occupancy image and Nav2 map metadata."""
    min_x, min_y, world_width, world_height, boxes = world_geometry(world_path)
    width = round(world_width / resolution)
    height = round(world_height / resolution)
    pixels = bytearray(width * height)

    for image_y in range(height):
        world_y = min_y + (height - image_y - 0.5) * resolution
        for image_x in range(width):
            world_x = min_x + (image_x + 0.5) * resolution
            occupied = any(box.contains(world_x, world_y) for box in boxes)
            pixels[image_y * width + image_x] = 0 if occupied else 254

    output_dir.mkdir(parents=True, exist_ok=True)
    pgm_path = output_dir / 'factory.pgm'
    pgm_path.write_bytes(f'P5\n{width} {height}\n255\n'.encode('ascii') + pixels)
    (output_dir / 'factory.yaml').write_text(
        'image: factory.pgm\n'
        'mode: trinary\n'
        f'resolution: {resolution:.2f}\n'
        f'origin: [{min_x:.2f}, {min_y:.2f}, 0.0]\n'
        'negate: 0\n'
        'occupied_thresh: 0.65\n'
        'free_thresh: 0.25\n',
        encoding='utf-8',
    )


def main() -> None:
    """Parse arguments and generate the map pair."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--world', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--resolution', type=float, default=0.05)
    arguments = parser.parse_args()
    if arguments.resolution <= 0:
        parser.error('--resolution must be greater than zero')
    render_map(arguments.world, arguments.output_dir, arguments.resolution)


if __name__ == '__main__':
    main()
