# Simulation-first portfolio demo runbook

This is the reproducible shot list for a 90–120 second technical demo. Record
from Ubuntu 24.04 with ROS 2 Jazzy and Gazebo Harmonic; use the committed
configuration and capture the terminal output alongside the video.

## Shot list

1. **Architecture (10 s).** Open `docs/portfolio/README.md` and show the
   architecture visual. State that the domain core is transport-independent and
   the digital twin shares the mission boundary with future hardware adapters.
2. **Digital twin bring-up (20 s).** Run the simulation smoke test and show the
   factory world, lidar/IMU topics, active controllers and commanded motion.
3. **Mapping and localization (20 s).** Run the mapping smoke test, show `/map`
   publishing, then show AMCL/Nav2 loading the versioned factory map.
4. **Mission and station handshake (25 s).** Dispatch a named waypoint mission,
   show the mission state transition, station lease correlation and PLC/MQTT
   grant before pseudo-docking.
5. **Degraded behavior (15 s).** Run the software fault campaign and show a
   stale telemetry or sensor-path scenario selecting hold/return-home rather
   than continuing blindly.
6. **Operations evidence (15 s).** Open Grafana and show robot, mission, lease,
   recovery and event panels. Finish on the acceptance visual and the JSON
   evidence artifact.

## Commands

```bash
source /opt/ros/jazzy/setup.bash
bash scripts/build_and_test_ros2.sh
timeout 240 bash scripts/smoke_test_simulation.sh
timeout 300 bash scripts/smoke_test_mapping.sh
timeout 360 bash scripts/smoke_test_navigation.sh
timeout 300 bash scripts/smoke_test_multi_robot.sh
python scripts/run_software_acceptance.py --runs 100
```

For the OT/IT dashboard demonstration:

```bash
cp deployment/.env.example .env
docker compose up --build --wait
```

Open Grafana at `http://127.0.0.1:3000` and use only demonstration credentials
from `.env`. Never include credentials in a portfolio recording.

## Recording rules

- Label the footage **simulation** and include the commit SHA in the opening or
  closing frame.
- Show the acceptance output; do not replace it with manually typed KPI overlays.
- Keep physical commissioning, E-stop validation and safety certification out
  of the simulation claim.
