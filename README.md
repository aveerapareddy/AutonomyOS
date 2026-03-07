# AutonomyOS

## Project Overview

AutonomyOS is an experimental robotics autonomy platform. The goal is to explore how modern AI systems can integrate with robotics simulation: natural language mission input, perception, autonomous navigation, and evaluation of behavior in reproducible scenarios.

The stack is Python (FastAPI, Pydantic) on the backend, PyBullet for simulation, with plans for LLM-based planning and perception integration. The project is built incrementally; the simulation and API layers are kept separate so that navigation, replay, and benchmarking can be added without blocking on a single integration path.

## Current Status

The repository currently provides:

- **Backend service scaffold** — FastAPI app with config, logging, and health endpoints.
- **Mission API and service layer** — POST/GET missions, request/response schemas, validation (e.g. non-empty mission text).
- **In-memory mission repository** — Missions stored in process; storage is behind an abstraction so it can be replaced with SQLite or another backend later.
- **PyBullet simulation environment** — Headless or GUI connection, single-robot scene.
- **Deterministic warehouse-style world** — Flat ground, static obstacles (walls, block), and one target (red cube). Layout is fixed for reproducibility.
- **Robot abstraction** — Single body in the sim with a minimal kinematic model.
- **Basic movement primitives** — Forward, backward, turn left, turn right, stop; pose exposed for logging and future navigation/replay.
- **Typed simulator API** — `RobotAction` enum, `BuiltWorld` metadata (world bounds, obstacle positions, target), and environment helpers (`get_world_bounds()`, `get_obstacles()`, `get_target_pose()`) for navigation and scenario use.
- **Occupancy-grid navigation foundation** — Grid built from world bounds and obstacle positions; configurable resolution and obstacle inflation (grid-cell radius).
- **A* path planning** over deterministic warehouse environments; Manhattan heuristic, 4-connected grid; path simplified by collapsing collinear waypoints.
- **Navigation demo** from robot start to target location (`run_navigation_demo.py`); no path execution yet.
- **Perception foundation with typed detection contracts** — `DetectedObject`, `PerceptionRequest`, `PerceptionResult`; same contract for a future YOLO-backed implementation.
- **Rule-based target and obstacle detection** from simulator metadata; confidence defaults in `core.constants`.
- **Object typing support** (target, wall, block) via `WorldObject` descriptor; `obstacle_objects` and `target_object` on `BuiltWorld` to avoid parallel-list drift.

The mission API and simulator are not yet connected; mission execution and replay are not implemented.

**Simulator architecture**

- **actions.py** — `RobotAction` enum (forward, backward, turn_left, turn_right, stop); used by `environment.step()` and the demo.
- **world_builder.py** — Builds a deterministic scene: ground plane, two walls, one block, one red target cube. Returns a `BuiltWorld` with `ground_id`, `obstacle_ids`, `obstacle_positions`, `obstacle_types` (wall/block), `target_id`, `target_position` (2D), `target_z`, and `world_bounds` (min_x, max_x, min_y, max_y).
- **robot.py** — Kinematic robot (box body); maintains (x, y, theta) and syncs to PyBullet; exposes `forward`, `backward`, `turn_left`, `turn_right`, `stop` and `get_pose()`.
- **environment.py** — Connects to PyBullet (DIRECT or GUI), builds world, spawns robot. Exposes `reset()`, `step(RobotAction)`, `get_robot_pose()`, `get_world_bounds()`, `get_obstacles()`, `get_obstacle_types()`, `get_target_pose()`, `shutdown()`. No API or mission coupling.
- **grid_map.py** — Builds a 2D occupancy grid from world bounds and obstacle positions; `world_to_grid`, `grid_to_world`, `is_blocked`, `neighbors` for path planning.
- **agents/navigation_agent.py** — A* path planning on an occupancy grid; accepts start/goal in world coords, returns world-space waypoints.
- **agents/perception_agent.py** — Rule-based perception from world metadata; returns `PerceptionResult` (targets, obstacles); swappable with YOLO later.
- **schemas/navigation.py** — Waypoint, NavigationRequest, NavigationResult.
- **schemas/perception.py** — DetectedObject, PerceptionRequest, PerceptionResult.

## Repository Structure

Run all commands from the repository root (the directory containing `backend/` and `scripts/`).

| Directory | Purpose |
|-----------|---------|
| `backend/` | Python package for the service and simulation. |
| `backend/api/` | FastAPI app and HTTP routes. |
| `backend/services/` | Business logic (e.g. mission lifecycle). |
| `backend/schemas/` | Pydantic models for API and internal contracts. |
| `backend/simulator/` | PyBullet world, robot, environment, occupancy grid. |
| `backend/agents/` | Navigation agent (A*), perception agent (rule-based from world metadata). |
| `backend/scenarios/` | Reserved for scenario generation (not yet implemented). |
| `backend/storage/` | Storage abstractions and repository implementations. |
| `scripts/` | One-off and demo scripts (e.g. simulator demo). |

## Development Setup

**Virtual environment**

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

**Dependencies**

```bash
pip install -r backend/requirements.txt
```

**Backend**

```bash
uvicorn backend.api.main:app --reload
```

API base URL: `http://127.0.0.1:8000` (or the host/port you configure). Health: `GET /health`. Missions: `POST /missions`, `GET /missions/{mission_id}`.

**Simulator demo**

```bash
python scripts/run_simulator_demo.py
```

**Navigation demo**

```bash
python scripts/run_navigation_demo.py
```

Builds an occupancy grid from the sim world, plans a path from robot pose to target, and prints start, target, path found, and waypoints. Does not move the robot.

**Perception demo**

```bash
python scripts/run_perception_demo.py
```

Runs the perception agent on the sim world metadata and prints detected targets and obstacles (object_id, type, x, y). No image-based detection; Phase-1 is rule-based from world state.

The simulator, navigation, and perception are tested with Python 3.11 and 3.12 on macOS (pybullet-mm for pip install).

Uses PyBullet in DIRECT (headless) mode, runs a short sequence of movements, and prints robot and target poses.

On macOS, `requirements.txt` pulls in `pybullet-mm` (a fork with macOS build fixes) instead of the official `pybullet` so the simulator can install with pip. If the build still fails (e.g. on very new macOS or Xcode), use conda:

```bash
conda create -n autonomyos python=3.12
conda activate autonomyos
conda install -c conda-forge pybullet
pip install -r backend/requirements.txt
```

Example output (pose format is (x, y, theta) for robot, (x, y, z) for target):

```
Robot start: (0.0, 0.0, 0.0)
Target: (5.0, 3.0, 0.15)
After forward x60: (0.125, 0.0, 0.0)
After turn_left x40: (0.125, 0.0, 0.16666666666666666)
After forward x40: (0.20713474435678494, 0.01383425925925926, 0.16666666666666666)
After turn_right x20: (0.20713474435678494, 0.01383425925925926, 0.08333333333333333)
After forward x30: (0.2694235857450433, 0.01898148148148148, 0.08333333333333333)
Done.
```

**Tests**

```bash
python -m pytest backend/tests/ -v
```

Mission API tests always run; simulator tests are skipped if PyBullet is not installed.

## Known Limitations

- Static planning only; world is fixed at plan time; no replanning or dynamic obstacles.
- No path execution yet; navigation produces waypoints only.
- Path simplification is collinear-only (reduces straight-line noise); no curve fitting or smoothing.
- Perception: metadata-based detection only; no image-based perception yet; no tracking across frames.

## Roadmap

- **Phase 1 — Core autonomy stack**  
  Connect mission API to the simulator; mission planning and execution loop; telemetry and basic replay/trace.

- **Phase 2 — YOLO perception integration**  
  Perception pipeline (e.g. OpenCV then YOLO) for object detection; feed observations into navigation and mission state.

- **Phase 3 — Reinforcement learning navigation**  
  Train or integrate policies for goal-directed navigation in the warehouse environment; optional LangGraph or similar for high-level control.

- **Phase 4 — Scenario benchmarking and evaluation**  
  Parameterized scenario generation; benchmark runs; metrics and evaluation for autonomy behavior.
