# Validation evidence

## 2026-11-07: dependency baseline and 3D projection

- Reproduced the original `npm ci` failure under Node 20.20.2 / npm 10.9.10: inconsistent chokidar and readdirp entries.
- Regenerated the lockfile without changing existing Angular dependency declarations.
- Clean `npm ci` and production `npm run build`: passed.
- Python 3.12.2, macOS ARM64, dependencies installed from backend/requirements.txt, `AUTONOMY_PLANNER_MODE=rule_based python -m pytest backend/tests -q`: 89 passed. Linux/Python 3.11 remains the CI gate.
- Added a lazy-loaded Three.js scene projected from the existing simulator scene model; obstacles, target, robot pose, planned path and executed path retain simulator coordinates.
- Browser verification: created and executed a mission, observed completed PyBullet execution, switched 3D to 2D and back, and verified the mission scene accessibility label updated.
- 3D uses orbit/zoom controls, bounded pixel density, resize observation and resource cleanup. Existing 2D view remains available.

## Open gates

- Original supplied reference image is absent from this checkout and the recovered chat. Visual parity is unverified.
- The 3D view currently shows execution results, not streaming simulation frames.
- Dependency audit reports 80 findings (7 low, 35 moderate, 33 high, 5 critical); remediation is pending the security milestone.
- No NVIDIA GPU run or hosted deployment has been validated.

## Durable telemetry and recorded replay increment

- `AUTONOMY_DATABASE_PATH=data/autonomy.sqlite3` opts API missions and telemetry into SQLite persistence. Without it, the existing in-memory behavior is retained.
- SQLite event sequence allocation occurs inside `BEGIN IMMEDIATE`, with a primary key on `(mission_id, sequence)` and per-operation connections. Tests reopen the database and exercise 100 concurrent writes across four independent journal instances.
- Executor emits `robot_state` every 24 simulation steps by reading `SimulationEnvironment.get_robot_pose()`. A real PyBullet test verifies sampled coordinates and heading against the final simulator pose.
- Telemetry supports `after_sequence` for reconnect/poll consumers. Replay and original event IDs survive restart.
- Angular offers play/pause, event scrub and result controls. Replay uses recorded event order at 10 events/second; playback is not simulation-time synchronized and is not a live stream.
- Mission/event durability does not yet imply durable orchestration checkpoints, execution resume or distributed workers.
