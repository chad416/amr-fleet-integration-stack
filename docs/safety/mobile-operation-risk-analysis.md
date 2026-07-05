# Mobile-operation Risk Analysis

Status: Preliminary design risk analysis. Not a certification artifact.

Risk ranking uses severity (S) and occurrence (O) from 1 to 5. Initial risk priority is `S x O`; residual values assume the listed controls are implemented and verified.

| Hazard | Cause | Effect | S | O | Engineering controls | Verification | Residual SxO |
|---|---|---|---:|---:|---|---|---:|
| Unexpected motion on startup | Stale command or automatic re-enable | Collision or injury | 5 | 2 | Zero-command timeout; lifecycle inactive by default; separate operator start | Cold/warm restart test | 5 |
| Failure to stop | Controller/network fault | Collision or injury | 5 | 2 | Independent E-stop chain; motor-enable removal; command watchdog | Physical stop test | 5 |
| Docking into occupied station | Concurrent grants or stale response | Collision/equipment damage | 4 | 3 | Exclusive expiring lease; mission/robot/lease correlation; approach hold | Concurrency and stale-message tests | 4 |
| Localization jump | Sensor/map ambiguity | Wrong path or collision | 4 | 3 | Pose-jump monitor; covariance threshold; cancel navigation and stop | Fault injection | 8 |
| Blind operation | Lidar/depth failure | Obstacle collision | 5 | 2 | Required sensor health; collision monitor; controlled degraded-mode policy | Sensor dropout test | 5 |
| Runaway velocity | Parameter or controller error | Collision or instability | 5 | 2 | Layered velocity limits; acceleration limits; independent drive limit | Limit tests | 5 |
| Communication loss at station | Wi-Fi/bridge failure | Unsafe transfer state | 4 | 3 | Fail-silent lease expiry; transfer requires live grant; PLC interlock | Network interruption test | 4 |
| Low battery during mission | Bad dispatch or battery estimation | Stranding in traffic lane | 3 | 3 | Dispatch reserve; critical threshold; charger diversion policy | Battery-boundary tests | 3 |
| Operator override conflict | Simultaneous autonomous/manual command | Unexpected motion | 5 | 2 | Command-source arbitration; deadman control; explicit mode state | Mode conflict test | 5 |

## Safety principles

- Software stop is not a substitute for a certified emergency-stop chain.
- Resetting a fault never authorizes motion by itself.
- Communication loss results in an inhibited or bounded state, not optimistic continuation.
- Safety-relevant parameters are version-controlled, reviewed, and included in FAT evidence.
- The physical risk assessment must be revisited after mass, speed, payload, stopping distance, and operating environment are known.

