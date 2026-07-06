# Verification and Validation Plan

Document ID: AMR-VVP-001  
Revision: A

## Verification levels

| Level | Scope | Environment | Gate |
|---|---|---|---|
| L0 | Domain invariants and algorithms | Any Python host | Every commit |
| L1 | ROS package build, lint, interface tests | ROS 2 Jazzy container | Every merge |
| L2 | Single-AMR digital twin | Gazebo Harmonic | Simulation FAT |
| L3 | Multi-AMR and station integration | Gazebo + PLC/OPC UA simulator | Integration FAT |
| L4 | Physical AMR | Controlled test area | SAT readiness |

## Initial traceability matrix

| Test ID | Requirement | Description | Level |
|---|---|---|---|
| T-DIS-001 | URS-F-004 | Lowest-cost eligible robot is selected deterministically | L0 |
| T-DIS-002 | URS-F-004 | Low-battery, stale, busy, degraded robots are rejected | L0 |
| T-STA-001 | URS-F-006, URS-P-003 | Concurrent station requests cannot both acquire access | L0 |
| T-STA-002 | URS-S-003 | Expired or mismatched lease cannot authorize docking | L0 |
| T-MIS-001 | URS-F-003, URS-F-009 | Nominal mission phase sequence completes | L0 |
| T-MIS-002 | URS-S-003 | Dock/transfer commands before access are rejected | L0 |
| T-MIS-003 | URS-F-009 | Pause/resume/cancel respects lifecycle constraints | L0 |
| T-API-001 | URS-F-003, URS-F-007, URS-P-004 | JSON/HTTP mission API accepts remote commands and translates domain errors | L0 |
| T-API-002 | URS-P-004 | 100 local API acknowledgements have p95 below 500 ms | L0 |
| T-FLT-001 | URS-F-004 | Batch dispatch skips busy robots and assigns queued missions to eligible idle robots | L0 |
| T-FLT-002 | URS-F-004, URS-F-008, URS-F-011, URS-F-012 | L0 fault campaign verifies stale robot, station busy, PLC stale heartbeat, recovery exhaustion and batch dispatch scenarios | L0 |
| T-TEL-001 | URS-F-007, URS-P-005, URS-F-012 | Telemetry projection marks stale robots and preserves audit event sequence | L0 |
| T-OBS-001 | URS-F-007 | Fleet snapshot and audit events export to Influx line protocol | L0 |
| T-ALM-001 | URS-F-007, URS-P-005 | Stale telemetry, critical battery and mission failures generate dashboard alarms | L0 |
| T-WAY-001 | URS-F-005 | Named station waypoints resolve to immutable mission stops | L0 |
| T-REC-000 | URS-F-008, URS-S-005 | Bounded recovery enters recovering, resumes safely, then fails after budget exhaustion | L0 |
| T-SIM-001 | URS-S-004 | Controllers, sensors and bounded commanded motion pass headless acceptance | L2 |
| T-MAP-001 | URS-F-001 | Versioned factory map is reproduced exactly from world collision geometry | L1 |
| T-MAP-002 | URS-F-001 | SLAM Toolbox publishes `/map` before and after bounded commanded motion | L2 |
| T-CMD-001 | URS-S-004 | Command adapter rejects non-finite input and clamps model limits | L1 |
| T-NAV-002 | URS-F-002, URS-F-005 | AMCL and Nav2 complete one deterministic headless waypoint goal | L2 |
| T-NAV-001 | URS-F-005, URS-P-001 | Approved route success over 100 seeded trials | L2 |
| T-REC-001 | URS-F-008, URS-P-002 | Blocked-path recovery succeeds within target | L2 |
| T-LOC-001 | URS-F-002, URS-P-006 | Cold-start localization at surveyed checkpoints | L2/L4 |
| T-OT-001 | URS-F-011 | OPC UA tag loss causes lease timeout and inhibits docking | L3 |
| T-OT-000 | URS-F-006, URS-F-011 | PLC simulator restart clears grants and station bridge inhibits stale docking | L0 |
| T-SAF-001 | URS-S-001, URS-S-002 | E-stop and reset/start separation | L4 |

## Evidence rules

- Automated results are saved as machine-readable JUnit XML in CI.
- Simulation FAT records configuration revision, random seed, map revision, and software commit.
- Timing claims include raw data, summary statistics, and host specifications.
- Failed tests remain in the report with disposition; they are not silently removed.
- Hardware SAT requires a witnessed checklist and photographs or video for physical controls.

## Latest L0 evidence

On 2026-07-06, the bundled Python runtime executed 41 L0 tests covering mission
lifecycle, dispatch, batch dispatch, named waypoints, station leases, JSON/HTTP API, telemetry
freshness, dashboard alarms, observability export, bounded recovery and PLC
bridge reconciliation. A
100-run fleet API benchmark completed 100 station missions successfully and
produced bounded recovery evidence where the third recovery request was rejected
with `RecoveryLimitExceeded` and the mission ended in `failed`.
The L0 fault campaign passed 5/5 scenarios for stale robot telemetry, station
busy rejection, stale PLC heartbeat, recovery exhaustion and batch dispatch.
