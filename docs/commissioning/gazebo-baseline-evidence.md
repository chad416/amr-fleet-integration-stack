# Gazebo Baseline Commissioning Evidence

Evidence date: 2026-07-05

Environment: `AMR-Ubuntu` under WSL2

## Environment record

| Item | Recorded value |
| --- | --- |
| Operating system | Ubuntu 24.04.4 LTS |
| Kernel | 6.18.33.2-microsoft-standard-WSL2 |
| Architecture | x86_64 |
| ROS distribution | Jazzy Jalisco |
| Gazebo Sim | 8.11.0 (Harmonic family) |
| `ros_gz` | 1.0.22-1noble.20260616.074726 |
| `gz_ros2_control` | 1.2.19-1noble.20260615.171757 |
| Navigation2 | 1.3.12-1noble.20260615.181551 |
| SLAM Toolbox | 2.8.5-1noble.20260615.161600 |
| CPU exposed to WSL2 | 13th Gen Intel Core i5-13450HX, 16 logical CPUs |
| Memory exposed to WSL2 | 11 GiB RAM, 3 GiB swap |
| Rendering mode used for acceptance | Headless Gazebo server |

The host GPU was not required for this headless gate and was not available to the
noninteractive hardware inventory query. GUI/rendering performance remains a
separate commissioning measurement.

## Configuration under test

- Factory world: `amr_simulation/worlds/factory.sdf`
- Launch orchestration: `amr_simulation/launch/simulation.launch.py`
- ROS/Gazebo bridge: `amr_simulation/config/bridge.yaml`
- Robot model: `amr_description/urdf/amr.urdf.xacro`
- Controller configuration: `amr_description/config/controllers.yaml`

Generated build, test and runtime evidence is written outside the OneDrive worktree
under `~/.cache/amr_fleet_ros`.

## Acceptance procedure

```bash
bash scripts/build_and_test_ros2.sh
bash scripts/smoke_test_simulation.sh
```

The smoke test is self-cleaning and fails closed when any required topic,
controller, or motion criterion is absent.

## Accepted results

| Check | Result |
| --- | --- |
| Factory world loads in headless Gazebo | Pass |
| AMR entity creation | Pass |
| `joint_state_broadcaster` active | Pass |
| `base_controller` active | Pass |
| Simulation clock delivered to ROS | Pass |
| 720-sample lidar scan delivered on `/scan` | Pass |
| IMU data delivered on `/imu/data` | Pass |
| Wheel odometry delivered on `/base_controller/odom` | Pass |
| Stamped velocity command accepted | Pass |
| Measured odometry displacement exceeds 0.05 m | Pass; 0.600 m observed |
| Simulation processes cleaned up after test | Pass |

The physics step is 1 ms and the controller period is 10 ms. Gazebo reports this
rate difference as a warning; it is intentional because physics runs at 1 kHz while
the controller manager runs at 100 Hz.

## Deferred acceptance

This gate does not claim autonomous navigation. Map generation, localization,
REP-105 `map -> odom` integration, Nav2 planning/control, collision recovery,
controller-limit characterization, GUI performance and long-duration soak testing
belong to later gates.
