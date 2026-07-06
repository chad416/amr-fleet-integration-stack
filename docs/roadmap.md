# Delivery Roadmap

The project is built in commissioning gates. Dates are intentionally not promised before the execution environment and hardware availability are known.

## Gate 0 - Engineering baseline

- Requirements, architecture, risk analysis, interface contract, and V&V plan
- Transport-independent mission, dispatch, and station-lease core
- CI and unit-test evidence

Exit: all L0 tests pass and requirements traceability has no orphaned implemented behavior.

## Gate 1 - Single-AMR digital twin

- Differential-drive URDF/Xacro and Gazebo world
- `ros2_control` differential-drive control
- Lidar, IMU, odometry, TF, and robot state publisher
- Headless runtime acceptance with commanded motion

Exit: repeatable world load, active controllers, live sensors, and verified motion
in simulation.

## Gate 2 - Autonomous navigation

- SLAM Toolbox mapping and map procedure
- Nav2 localization, planning, control, and recovery configuration
- Lifecycle-managed bring-up

Exit: repeatable mapping/localization plus approved waypoint mission in simulation.

## Gate 3 - Fleet vertical slice

- ROS 2 adapter around the domain core **implemented as `amr_fleet_adapter`**
- Remote mission API **implemented in JSON/HTTP form**
- Named waypoints and docking approach poses
- Robot heartbeat, battery, pose, mission, and health telemetry **implemented
  as read-only projections and API audit events**
- Pause, resume, cancel, and bounded recovery **implemented in the domain/API**

Exit: 100-run single-robot mission benchmark and fault-recovery evidence.

Status: the transport-independent API/recovery/telemetry slice has exit
evidence. The ROS 2 action/service/topic adapter package is implemented and
covered by pure contract tests. Gate 3 remains open until the adapter is built
and accepted in Jazzy with generated ROS interfaces.

## Gate 4 - Industrial station integration

- OPC UA server simulator matching the material-handling handshake
- Station bridge and lease reconciliation **implemented at the domain boundary**
- OPC UA/MQTT transport codecs **implemented at the boundary**
- InfluxDB/Grafana dashboards and alarm events **implemented as line-protocol
  exporter, audit events and importable dashboard JSON**
- Network loss, stale message, and PLC restart tests

Exit: L3 integration FAT with zero station mutual-exclusion violations.

Status: PLC handshake simulation, stale heartbeat inhibition, restart behavior,
OPC UA/MQTT codecs, Influx export and Grafana dashboard JSON are covered by L0
tests. Gate 4 remains open until the actual OPC UA/MQTT server/client processes
and Grafana runtime are deployed.

## Gate 5 - Multi-robot fleet

- Two or more simulated robots with namespace isolation **scaffold implemented**
- Traffic and station resource coordination
- Charge mission policy and battery-aware allocation
- Load and soak testing

Exit: multi-robot mission KPI report with traceable failure analysis.

Status: deterministic batch dispatch across multiple eligible robots is covered
at L0, and the two-robot Gazebo namespace/spawn scaffold is present. Gate 5
remains open until multi-robot Gazebo runtime traffic, charging policy and soak
testing are implemented.

## Gate 6 - Physical commissioning

- Hardware selection and approved electrical/mechanical design
- Motor, encoder, sensor, battery, bumper, and independent E-stop integration
- Calibration, stopping-distance tests, and controlled-area SAT
- Simulation-versus-real comparison report

Exit: witnessed SAT evidence. No safety certification claim is made without the required certified process and components.
