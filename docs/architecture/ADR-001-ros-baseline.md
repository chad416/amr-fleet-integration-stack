# ADR-001: ROS and Simulator Baseline

Status: Accepted  
Date: 2026-07-05

## Decision

Use ROS 2 Jazzy Jalisco on Ubuntu 24.04 with Gazebo Harmonic for the first commissioned baseline.

## Context

ROS 2 Lyrical is the newest LTS release as of this decision, but it is newly released. Jazzy remains supported until May 2029 and has a mature, officially paired Gazebo Harmonic integration plus active Nav2 support. The project values reproducibility and ecosystem maturity over adopting the newest distribution immediately.

The version boundary is isolated behind ROS adapters. The mission, dispatch, station-access, and telemetry domain code does not import `rclpy`, which reduces migration risk.

## Consequences

- Ubuntu 24.04 is the reference operating system.
- ROS packages target Jazzy APIs and quality level.
- The baseline is reviewed annually or when a required package drops Jazzy support.
- Migration to Lyrical requires a dependency compatibility matrix and full simulation regression, not an in-place unreviewed upgrade.

## Sources

- ROS 2 distributions: <https://docs.ros.org/en/jazzy/Releases.html>
- Nav2 lifecycle management: <https://docs.nav2.org/configuration/packages/configuring-lifecycle.html>
- Gazebo ROS 2 vendor pairing: <https://gazebosim.org/docs/harmonic/ros2_gz_vendor_pkgs/>

