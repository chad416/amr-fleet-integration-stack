# Map Management Procedure

## Purpose

This procedure controls how a map is created, reviewed, versioned, deployed and
retired. A map is configuration data that changes robot behavior; it is not an
untracked operator artifact.

## Map identities

The repository contains two map paths with different purposes:

- `amr_navigation/maps/factory.pgm` is the deterministic simulation truth used by
  localization and repeatable acceptance testing.
- Maps captured with SLAM Toolbox are commissioning candidates. They are not
  approved for navigation until reviewed and committed with metadata.

The factory map is generated from static collision geometry in
`amr_simulation/worlds/factory.sdf`. The contract test rejects world changes that
were not reflected in the committed map.

## Regenerate the simulation map

After changing static factory collision geometry:

```bash
ros2 run amr_navigation generate_factory_map.py \
  --world ros_ws/src/amr_simulation/worlds/factory.sdf \
  --output-dir ros_ws/src/amr_navigation/maps
bash scripts/build_and_test_ros2.sh
bash scripts/smoke_test_mapping.sh
```

Review the occupancy image, named-waypoint clearance and generated diff before
committing both the SDF and map in the same change.

## Create a SLAM candidate

```bash
ros2 launch amr_navigation mapping.launch.py headless:=false
```

Drive a coverage route at conservative speed. Close loops from multiple headings,
avoid moving obstacles where practical, and verify that lidar returns are not
clipped by the robot footprint. Save the map only after the loop-closure solution
has stabilized:

```bash
ros2 run nav2_map_server map_saver_cli -f /tmp/factory_candidate
```

## Candidate review gate

A candidate requires all of the following before deployment:

1. Record site, timestamp, ROS/SLAM versions, sensor calibration revision and
   operator.
2. Confirm scale against at least two independently measured floor distances.
3. Check walls and fixed equipment for duplication, bowing and discontinuities.
4. Verify all approved waypoints have footprint plus inflation clearance.
5. Cold-start AMCL at representative approved poses.
6. Perform kidnapped-robot relocalization and blocked-route recovery tests.
7. Run the waypoint acceptance suite and archive its evidence.

## Versioning and rollback

Store the image and YAML metadata together under `maps/<site>/<revision>/`. Commit
the files, waypoint update and evidence as one atomic change. Deployment records
must identify the Git commit rather than a mutable filename alone.

Keep the previous approved map available for rollback. Never overwrite the last
known-good map on a robot until the new revision passes cold-start localization and
a controlled low-speed route. A rollback must restore the matching map, waypoint
set and navigation parameters.
