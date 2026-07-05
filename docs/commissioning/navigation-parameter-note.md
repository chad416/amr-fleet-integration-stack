# Navigation Parameter Engineering Note

## Coordinate and topic contract

The autonomy stack follows REP-105 semantics:

```text
map -> odom -> base_footprint -> base_link -> sensor frames
```

- AMCL owns `map -> odom` during localization.
- The differential-drive controller owns `odom -> base_footprint`.
- Robot State Publisher owns fixed robot transforms.
- Lidar input is `/scan`; odometry input is `/base_controller/odom`.

The initial simulation pose is `(-3.5, 0.0, 0.0)` in both Gazebo and AMCL. A real
deployment must not reuse that assumption; an operator, fiducial or localization
supervisor must provide a validated initial pose.

## Geometry and clearance

The body is 0.55 m long by 0.42 m wide. Costmaps use a conservative rectangular
footprint of 0.59 m by 0.46 m plus 0.02 m padding. Inflation radius is 0.55 m with
a cost scaling factor of 3.0. These are commissioning defaults, not final physical
robot values.

The global costmap combines the versioned static map with current lidar obstacles.
The local rolling costmap uses lidar obstacles and inflation at 5 cm resolution.

## Planning and control

- Smac 2D provides grid planning with a 0.20 m goal tolerance.
- Regulated Pure Pursuit is limited to 0.45 m/s nominal travel and slows for
  curvature, cost and goal approach.
- The velocity smoother applies the model's 0.70 m/s² acceleration and
  0.90 m/s² deceleration limits with closed-loop odometry feedback.
- The controller rejects lack of progress after 12 seconds and bounds recovery
  actions through the behavior server.

The headless Gate 2 acceptance route is the named `inspection_west` waypoint:
`(-2.4, -1.5, 0.0)` in the `map` frame from the default simulation start pose.
The farther south-west point `(-2.0, -2.0, 0.0)` is intentionally not used as the
baseline smoke target because it crosses the current planner/costmap envelope
near inflated obstacles and belongs in the later route-matrix tuning campaign.

## Protective command chain

Command velocity follows one explicit chain:

```text
controller/behaviors -> cmd_vel_nav -> velocity smoother
-> cmd_vel_smoothed -> collision monitor -> cmd_vel adapter
-> base_controller/cmd_vel
```

The collision monitor has an inner stop polygon and outer slowdown polygon. It is
a non-certified software protective layer. ROS 2 Jazzy Nav2 emits `Twist`, while
the Jazzy differential-drive controller consumes `TwistStamped`; the adapter
validates finite values, removes holonomic components, clamps model limits and adds
the simulation timestamp.

This command chain does not replace a safety-rated scanner, drive STO, independent
emergency stop or validated stopping-distance calculation.

## Required tuning evidence

Before physical deployment, measure and record:

- wheel radius, wheel separation and encoder scale;
- straight-line and angular odometry error;
- maximum loaded acceleration and emergency deceleration;
- scan timestamp latency and TF age;
- minimum stopping distance at each permitted speed;
- planner/controller success over the approved route set;
- recovery duration and operator escalation behavior.

Parameter changes require a reason, before/after KPI evidence and a rollback point.
