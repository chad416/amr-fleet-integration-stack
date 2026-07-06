# AMR and Fleet Integration Stack

An industrial-grade, simulation-first autonomous mobile robot platform demonstrating mission dispatch, ROS 2 navigation, station handshakes, fault recovery, telemetry, and OT integration.

## Engineering intent

This repository is designed as commissioning evidence, not as a one-off robot demo. The same mission and fleet domain model is used by simulation and future hardware adapters. Every capability is traced to a requirement and a verification method.

Current baseline:

- ROS 2 Jazzy Jalisco on Ubuntu 24.04
- Gazebo Harmonic digital twin
- Nav2, SLAM Toolbox, and `ros2_control`
- Transport-independent Python domain core
- OPC UA/MQTT station integration boundary
- InfluxDB/Grafana observability boundary

The project does **not** claim a certified safety function. Emergency-stop and protective-stop behavior are safety-oriented integration concepts that must ultimately be implemented and validated with certified hardware.

## Current status

| Capability | Status | Evidence |
|---|---|---|
| Mission lifecycle and invariants | Implemented | Unit tests |
| Deterministic robot dispatch | Implemented | Unit tests |
| Batch fleet dispatch | Implemented | Multi-robot unit tests |
| Exclusive station access lease | Implemented | Unit tests |
| ROS 2 interfaces | Implemented and compiled | Colcon build evidence |
| Differential-drive AMR model | Implemented and compiled | Xacro, controller configuration, Linux build |
| Gazebo simulation baseline | Implemented and runtime accepted | Factory world, launch orchestration, bridge and motion smoke test |
| Nav2 integration | Implemented and runtime accepted | Versioned map, AMCL, planner, controller, collision monitor, command adapter and waypoint smoke test |
| Remote fleet mission API | Implemented and benchmarked | JSON/HTTP adapter, unit tests, 100-run benchmark |
| Named station waypoints | Implemented | Waypoint catalog and API named-stop tests |
| Bounded recovery | Implemented at fleet/API layer | Recovery unit tests and benchmark evidence |
| PLC/OPC UA station handshake | Core implemented | Station bridge, PLC simulator, lease reconciliation tests |
| Fleet telemetry dashboards | Export core implemented | Telemetry projection, alarm evaluation and Influx line-protocol exporter |
| Physical AMR commissioning | Hardware-dependent | Commissioning checklist |

## Repository map

```text
config/                 Fleet, station, and deployment configuration
docs/                   Requirements, architecture, safety, V&V, commissioning
ros_ws/src/
  amr_fleet_core/       Mission, dispatch, station access, telemetry domain
  amr_interfaces/       ROS 2 messages, services, and actions
  amr_description/      Robot model and ros2_control configuration
  amr_simulation/       Gazebo world, bridge and repeatable launch system
  amr_navigation/       Mapping, localization, Nav2 and versioned factory map
ros_ws/src/amr_fleet_core/test/
                        Transport-independent verification suite
scripts/benchmark_fleet_api.py
                        100-run fleet API and recovery evidence benchmark
```

## Run the domain verification suite

The first vertical slice intentionally runs without ROS so that mission safety invariants are verified on any developer machine:

```bash
python -m pip install --editable ".[dev]"
python -m unittest discover -s ros_ws/src/amr_fleet_core/test -v
```

For full ROS/Gazebo commissioning, use Ubuntu 24.04 (native or WSL2) and follow [the simulation commissioning checklist](docs/commissioning/simulation-checklist.md).

Bootstrap an Ubuntu 24.04 environment with:

```bash
sudo bash scripts/bootstrap_ros2_jazzy.sh
bash scripts/verify_ros2_environment.sh
bash scripts/build_and_test_ros2.sh
bash scripts/smoke_test_simulation.sh
bash scripts/smoke_test_mapping.sh
bash scripts/smoke_test_navigation.sh
python scripts/benchmark_fleet_api.py --runs 100
```

Generated ROS build, install, and test artifacts are kept on the Linux filesystem at `~/.cache/amr_fleet_ros`. This avoids severe performance and file-locking problems when a WSL build writes thousands of generated files into a Windows or OneDrive mount.

## Core guarantees in the current slice

- A mission cannot execute before assignment to an available robot.
- A robot below the dispatch battery reserve is not assigned work.
- A mission cannot dock or transfer without a live station lease.
- One station grants at most one active lease.
- Terminal mission states cannot be reopened accidentally.
- Dispatch decisions are deterministic for identical fleet state.
- Batch dispatch skips busy robots and assigns queued missions to eligible idle
  robots.
- Remote mission commands return protocol-safe API responses.
- Named station waypoints resolve to immutable approach poses at the fleet
  boundary.
- Bounded recovery resumes only within its configured attempt budget and fails
  safe when the budget is exhausted.
- Dashboard alarms are derived from read-only telemetry snapshots.
- PLC station grants are accepted only when the fleet lease and PLC correlation
  match and fresh heartbeat data is present.

## Documentation index

- [Current completion status](docs/STATUS.md)
- [User requirements specification](docs/requirements/URS.md)
- [System architecture](docs/architecture/system-architecture.md)
- [ROS baseline decision](docs/architecture/ADR-001-ros-baseline.md)
- [Mission and station interface](docs/interfaces/mission-and-station-interface.md)
- [Mobile-operation risk analysis](docs/safety/mobile-operation-risk-analysis.md)
- [Verification and validation plan](docs/verification/verification-plan.md)
- [Simulation commissioning checklist](docs/commissioning/simulation-checklist.md)
- [Gazebo baseline evidence](docs/commissioning/gazebo-baseline-evidence.md)
- [Map management procedure](docs/commissioning/map-management.md)
- [Navigation parameter engineering note](docs/commissioning/navigation-parameter-note.md)
- [Delivery roadmap](docs/roadmap.md)

## License

Apache-2.0. See [LICENSE](LICENSE).
