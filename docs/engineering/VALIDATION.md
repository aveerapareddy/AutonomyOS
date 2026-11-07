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

## Security and deployment preparation increment

- Migrated Angular 18 → 19 → 20 → 21 using Angular migrations; production build passed at each major. Final clean install/build passed with Angular 21.2.26 and CLI 21.2.29 under Node 20.20.2/npm 10.9.10.
- Final production npm audit: 0 findings. Full audit: 21 moderate findings in development/build tooling, 0 high/critical. These remain tracked, not suppressed.
- Python regression suite after public-demo policy and input validation changes: 96 passed locally.
- Browser verified Angular 21 production assets served at `/demo/` by FastAPI, mission creation and completed PyBullet execution.
- Actual HTTP smoke: 202 ordered events, real sampled robot states, replay, cursor reconnect and public batch blocking passed. Stopped and restarted the local server; the same mission and replay remained available and the restart smoke passed.
- First Docker CI caught missing Python 3.12 PyBullet wheels/compiler. The image was corrected to Python 3.11 and NumPy 2.3.5. Container CI result is tracked in GitHub Actions; a prepared image is not a hosted deployment.

## Container and geometry gates

- CI run 42425524264 passed backend, frontend and container-demo jobs. Container smoke executed a real mission and verified persisted telemetry/replay after container restart. The CPU image includes the planner's required `httpx` import even when rule-based mode is selected.
- Added obstacle half-extents to the backward-compatible scene contract; 2D/3D views now project the long default warehouse walls rather than drawing all obstacles as square blocks.
- A real PyBullet AABB comparison verifies published default obstacle extents against physics bodies. The local regression suite now has 97 passing tests; production Angular build passes after the geometry change.
