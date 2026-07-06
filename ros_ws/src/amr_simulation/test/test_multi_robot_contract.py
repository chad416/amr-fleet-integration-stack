# Copyright 2026 AMR Fleet Integration Stack Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");

"""Static acceptance tests for the multi-robot simulation scaffold."""

from pathlib import Path

import yaml


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def test_multi_robot_config_has_unique_namespaces_entities_and_frame_prefixes() -> None:
    with (PACKAGE_ROOT / "config" / "multi_robot_fleet.yaml").open(encoding="utf-8") as stream:
        config = yaml.safe_load(stream)

    robots = config["robots"]
    assert len(robots) >= 2
    assert len({robot["id"] for robot in robots}) == len(robots)
    assert len({robot["namespace"] for robot in robots}) == len(robots)
    assert len({robot["entity_name"] for robot in robots}) == len(robots)
    assert len({robot["frame_prefix"] for robot in robots}) == len(robots)
    assert all(robot["namespace"].startswith("/") for robot in robots)
    assert all(robot["frame_prefix"].endswith("/") for robot in robots)


def test_multi_robot_spawn_poses_are_separated() -> None:
    with (PACKAGE_ROOT / "config" / "multi_robot_fleet.yaml").open(encoding="utf-8") as stream:
        config = yaml.safe_load(stream)

    poses = [
        (robot["spawn"]["x"], robot["spawn"]["y"], robot["spawn"]["yaw"])
        for robot in config["robots"]
    ]
    assert len(set(poses)) == len(poses)
    assert abs(poses[0][1] - poses[1][1]) >= 1.0


def test_multi_robot_launch_uses_namespaced_robot_description_topics() -> None:
    launch_text = (
        PACKAGE_ROOT / "launch" / "multi_robot_simulation.launch.py"
    ).read_text(encoding="utf-8")

    assert "PushRosNamespace(namespace)" in launch_text
    assert "frame_prefix" in launch_text
    assert "/{namespace}/robot_description" in launch_text
    assert "allow_renaming" in launch_text
