# Simulation Commissioning Checklist

This is the controlled bring-up order for the Gazebo/Nav2 baseline. Items are checked only when evidence exists.

## Environment

- [x] Ubuntu 24.04 host or WSL2 environment recorded.
- [x] ROS 2 Jazzy package versions captured.
- [x] Gazebo Harmonic and `ros_gz` versions captured.
- [ ] Repository commit and configuration checksum recorded.
- [ ] Host CPU, RAM, and GPU recorded.

## Robot model and control

- [x] URDF/Xacro validates with no missing transforms.
- [ ] Mass and inertia values are physically plausible and documented.
- [x] Wheel radius and separation match the model.
- [ ] Joint state and odometry rates meet configuration targets.
- [ ] Velocity and acceleration limits are enforced.
- [ ] Command timeout produces zero velocity.

## Sensors and localization

- [ ] Lidar/depth scan frame and timestamp are correct.
- [ ] IMU orientation and covariance are correct where used.
- [ ] TF tree satisfies REP-105 (`map -> odom -> base_link`).
- [ ] SLAM map is saved with revision metadata.
- [ ] AMCL cold-start and relocalization tests pass.

## Navigation

- [ ] Global planner produces valid paths for all approved routes.
- [ ] Local controller respects footprint and speed limits.
- [ ] Collision monitor behavior is tested.
- [ ] Blocked-path recovery is bounded and observable.
- [ ] Unknown-pose startup is rejected safely.

## Fleet and OT integration

- [ ] Remote mission submission returns an immutable mission ID.
- [ ] Dispatch excludes stale, busy, degraded, and low-battery robots.
- [ ] Station access is exclusive under concurrent requests.
- [ ] Lease expiry inhibits docking/transfer.
- [ ] PLC/OPC UA simulator disconnect is handled.
- [ ] Mission and fault telemetry reach the dashboard.

## FAT exit gate

- [ ] All L0 and L1 tests pass.
- [ ] No open severity-5 risk lacks an implemented control.
- [ ] 100-run mission benchmark meets the URS target.
- [ ] Known deviations are recorded with owner and disposition.
- [ ] FAT report is signed and archived under `artifacts/fat/<revision>/`.
