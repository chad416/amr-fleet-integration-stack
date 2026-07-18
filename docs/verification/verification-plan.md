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
| T-ROS-001 | URS-F-003, URS-F-007, URS-F-009 | ROS fleet adapter maps ExecuteMission goals to validated domain mission payloads | L0 |
| T-FLT-001 | URS-F-004 | Batch dispatch skips busy robots and assigns queued missions to eligible idle robots | L0 |
| T-FLT-002 | URS-F-004, URS-F-008, URS-F-011, URS-F-012 | L0 fault campaign verifies stale robot, station busy, PLC stale heartbeat, recovery exhaustion and batch dispatch scenarios | L0 |
| T-TRF-001 | URS-F-006 | Traffic zones grant one live reservation and reject conflicting robots | L0 |
| T-CHG-001 | URS-F-004 | Low-battery available robots are selected for charge missions in deterministic priority order | L0 |
| T-TRF-002 | URS-F-004, URS-P-003 | Multi-zone routes reserve atomically in a global order and roll back completely on conflict | L0 |
| T-DCK-001 | URS-F-006, URS-S-003 | Pseudo-docking holds without a fresh grant and accepts bounded commands only inside the station sequence | L0/L3 |
| T-SUP-001 | URS-F-010, URS-S-002 | Localization, perception and network loss select safe hold/return-home modes; E-stop reset requires separate start | L0/L1 |
| T-TEL-001 | URS-F-007, URS-P-005, URS-F-012 | Telemetry projection marks stale robots and preserves audit event sequence | L0 |
| T-OBS-001 | URS-F-007 | Fleet snapshot and audit events export to Influx line protocol | L0 |
| T-OBS-002 | URS-F-007 | Grafana dashboard artifact contains robot, mission, lease, recovery and event panels | L0 |
| T-ALM-001 | URS-F-007, URS-P-005 | Stale telemetry, critical battery and mission failures generate dashboard alarms | L0 |
| T-WAY-001 | URS-F-005 | Named station waypoints resolve to immutable mission stops | L0 |
| T-REC-000 | URS-F-008, URS-S-005 | Bounded recovery enters recovering, resumes safely, then fails after budget exhaustion | L0 |
| T-SIM-001 | URS-S-004 | Controllers, sensors and bounded commanded motion pass headless acceptance | L2 |
| T-SIM-002 | URS-F-004 | Two-AMR simulation launch/config uses unique namespaces, entities, frame prefixes and spawn poses | L1 |
| T-MAP-001 | URS-F-001 | Versioned factory map is reproduced exactly from world collision geometry | L1 |
| T-MAP-002 | URS-F-001 | SLAM Toolbox publishes `/map` before and after bounded commanded motion | L2 |
| T-CMD-001 | URS-S-004 | Command adapter rejects non-finite input and clamps model limits | L1 |
| T-NAV-002 | URS-F-002, URS-F-005 | AMCL and Nav2 complete one deterministic headless waypoint goal | L2 |
| T-NAV-001 | URS-F-005, URS-P-001 | Approved route success over 100 seeded trials | L2 |
| T-REC-001 | URS-F-008, URS-P-002 | Blocked-path recovery succeeds within target | L2 |
| T-LOC-001 | URS-F-002, URS-P-006 | Cold-start localization at surveyed checkpoints | L2/L4 |
| T-OT-001 | URS-F-011 | OPC UA tag loss causes lease timeout and inhibits docking | L3 |
| T-OT-000 | URS-F-006, URS-F-011 | PLC simulator restart clears grants and station bridge inhibits stale docking | L0 |
| T-OT-002 | URS-F-011 | OPC UA write/snapshot mapper and MQTT command/status codec preserve station and lease correlation | L0 |
| T-OT-003 | URS-F-006, URS-F-011, URS-P-003 | Live MQTT coordinator and PLC simulator complete correlated station missions without mutual-exclusion violation | L0/L3 |
| T-OBS-003 | URS-F-007 | InfluxDB v2 writer authenticates, retries within a bound and exports each audit event once | L0/L3 |
| T-DEP-001 | URS-F-007, URS-F-011 | Compose deployment validates and the non-root runtime image builds in CI | L1 |
| T-SWF-001 | URS-F-003, URS-F-006, URS-F-010, URS-F-011, URS-P-003, URS-P-004 | 100-run aggregate software FAT covers MQTT docking, station contention, traffic rollback and degraded modes | L1/L3 |
| T-SAF-001 | URS-S-001, URS-S-002 | E-stop and reset/start separation | L4 |

## Evidence rules

- Automated results are saved as machine-readable JUnit XML in CI.
- Simulation FAT records configuration revision, random seed, map revision, and software commit.
- Timing claims include raw data, summary statistics, and host specifications.
- Failed tests remain in the report with disposition; they are not silently removed.
- Hardware SAT requires a witnessed checklist and photographs or video for physical controls.

## Latest software evidence

On 2026-07-07, GitHub Actions run
[28881834692](https://github.com/chad416/amr-fleet-integration-stack/actions/runs/28881834692)
passed the complete software acceptance chain at commit
`39ccf7ea94ad43d1b1f642e7c74ab455e3c7e9af`: domain-core lint/type/unit/adapter
contracts, software FAT, Compose validation, non-root runtime-image build, ROS
Jazzy package build/test, single-AMR Gazebo smoke acceptance, SLAM mapping,
AMCL/Nav2 waypoint acceptance and multi-AMR Gazebo smoke acceptance.

The Python 3.12 quality gate executed 73 L0 tests covering mission
lifecycle, dispatch, batch dispatch, named waypoints, station leases, JSON/HTTP
API, autonomy supervision, pseudo-docking, atomic route coordination, live MQTT
station automation, InfluxDB export, deployment contracts, telemetry freshness,
dashboard alarms, bounded recovery and PLC bridge reconciliation. A
100-run fleet API benchmark completed 100 station missions successfully and
produced bounded recovery evidence where the third recovery request was rejected
with `RecoveryLimitExceeded` and the mission ended in `failed`.
The L0 fault campaign passed 5/5 scenarios for stale robot telemetry, station
busy rejection, stale PLC heartbeat, recovery exhaustion and batch dispatch.
The aggregate software FAT completed 100/100 MQTT station missions, rejected
100/100 concurrent contenders, recorded zero mutual-exclusion violations,
rejected 100/100 traffic conflicts with zero rollback failures or deadlocks, and
passed all five degraded-mode scenarios. The committed machine-readable FAT
artifact is `docs/verification/evidence/software-acceptance-20260707T163135Z.json`.

The 2026-07-18 publication-readiness rerun passed the same aggregate campaign
after the host-side ROS command-boundary test was made import-safe outside a ROS
runtime. It completed 100/100 station missions, rejected 100/100 traffic
conflicts, recorded zero station mutual-exclusion violations, zero rollback
failures/deadlocks and 5/5 degraded-mode scenarios. The machine-readable
artifact is `docs/verification/evidence/software-acceptance-20260718T101127Z.json`.
