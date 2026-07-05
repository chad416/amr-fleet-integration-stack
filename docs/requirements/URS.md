# User Requirements Specification

Document ID: AMR-URS-001  
Revision: A  
Status: Baseline

## Scope

The system shall demonstrate a differential-drive AMR and fleet integration platform in simulation first, then preserve the same interfaces for physical deployment. It covers mapping, localization, waypoint missions, station access, fault recovery, telemetry, and industrial supervisory integration.

## Functional requirements

| ID | Requirement | Acceptance method |
|---|---|---|
| URS-F-001 | The AMR shall create and persist a 2D occupancy map. | Demonstration and map artifact review |
| URS-F-002 | The AMR shall localize on an approved map after restart. | Ten cold-start trials |
| URS-F-003 | An operator or fleet client shall submit a waypoint mission remotely. | API integration test |
| URS-F-004 | The fleet manager shall assign work only to an eligible available robot. | Automated tests |
| URS-F-005 | The AMR shall navigate to named pickup, drop-off, and charging waypoints. | Simulation FAT |
| URS-F-006 | The AMR shall request and receive exclusive station access before docking. | Automated and integration tests |
| URS-F-007 | The AMR shall expose mission, pose, battery, health, and fault telemetry. | Interface inspection and dashboard test |
| URS-F-008 | The AMR shall attempt bounded recovery after a blocked path. | Obstacle-injection test |
| URS-F-009 | The AMR shall support operator pause, resume, and cancel commands. | Automated and simulation tests |
| URS-F-010 | The AMR shall transition to a defined degraded or failed state after loss of required localization or communication. | Fault-injection test |
| URS-F-011 | The stack shall support an OPC UA or MQTT boundary to a material-handling cell. | Contract and integration test |
| URS-F-012 | The fleet manager shall reject stale robot telemetry for dispatch decisions. | Automated clock-controlled test |

## Performance requirements

| ID | Requirement | Target |
|---|---|---|
| URS-P-001 | Mission success rate in the approved simulation test route | >= 95% over 100 runs |
| URS-P-002 | Mean recovery time after a transient blocked path | <= 30 s |
| URS-P-003 | Station mutual-exclusion violations | 0 |
| URS-P-004 | Fleet API mission acknowledgement | <= 500 ms at p95 on the reference host |
| URS-P-005 | Telemetry freshness while connected | <= 3 s old |
| URS-P-006 | Localization error at surveyed checkpoints | <= 0.15 m position, <= 5 degrees yaw |

## Safety-oriented requirements

| ID | Requirement | Acceptance method |
|---|---|---|
| URS-S-001 | Emergency-stop input shall inhibit commanded motion through the hardware control chain. | Physical commissioning test |
| URS-S-002 | The software shall never represent an E-stop reset as permission to move; a separate operator start is required. | State-machine test |
| URS-S-003 | Loss of station-access permission shall prevent docking or transfer initiation. | Automated and integration tests |
| URS-S-004 | Commanded velocity shall be limited by configured linear and angular bounds. | Parameter and runtime test |
| URS-S-005 | The system shall record safety-relevant state changes with monotonic ordering. | Log inspection |

## Constraints and assumptions

- Simulation uses ROS 2 Jazzy and Gazebo Harmonic on Ubuntu 24.04.
- The first physical target is a differential-drive platform with wheel encoders, lidar or depth sensing, bumpers, and an independent E-stop chain.
- Network loss is normal and shall be handled explicitly.
- This project demonstrates safety-oriented engineering only; it makes no SIL or PL certification claim.

## Traceability rule

Each implementation pull request shall cite one or more requirement IDs. Every baseline requirement shall have at least one verification case before FAT completion.

