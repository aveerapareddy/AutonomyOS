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
- **Telemetry and mission event logging** — Event-driven telemetry with stable event types (e.g. mission_received, plan_generated, path_computed); in-memory store; GET `/missions/{mission_id}/telemetry` returns ordered event timeline. Mission creation emits `mission_received`. Telemetry is the foundation for mission replay and benchmarking; replay and benchmark runs are not implemented yet.
- **Event-driven telemetry foundation** — Per-mission monotonic sequence and timestamp; stable event types and source-component constants for replay and trace filtering.
- **Mission timeline retrieval API** — GET `/missions/{mission_id}/telemetry` returns events in order (sequence, then timestamp).
- **Replay-ready event contracts** — TelemetryEvent (event_id, mission_id, sequence, timestamp, event_type, source_component, payload) and TelemetryEventType enum.
- **First end-to-end orchestration flow** — POST `/missions/{mission_id}/execute` runs plan-perceive-navigate; returns `MissionExecutionSummary`; 404 when mission not found.
- **Rule-based mission planning** — Keyword-derived plan steps (e.g. "red", "avoid"); no LLM yet.
- **Perception + navigation coordination** — Orchestrator loads layout, runs perception, selects target, plans path; clear failure paths for no target / no path.
- **Replay-ready telemetry events during execution** — plan_generated, perception_completed, path_computed, mission_completed, mission_failed with stable source_component (planner, perception_agent, navigation_agent). Success path: 5 events (mission_received at create plus 4 during execute).
- **Waypoint execution engine for simulator-based mission runs** — WaypointExecutor drives the robot through navigation waypoints; ExecutionService owns sim lifecycle (create env, run executor, shutdown). Configurable tolerance and max steps per waypoint.
- **End-to-end mission pipeline from planning to execution** — POST execute runs plan, perceive, navigate, then sim execution; MissionExecutionSummary includes execution_steps, final_robot_position, execution_status.
- **Execution telemetry for waypoint completion and mission status** — execution_started, waypoint_reached, execution_completed, execution_failed with source_component execution_engine; mission_completed/mission_failed from orchestrator_service. Stable source names: planner, perception_agent, navigation_agent, execution_engine, orchestrator_service.
- **Mission replay foundation** — GET `/missions/{mission_id}/replay` returns event-driven replay (MissionReplay: frames from telemetry). ReplayService builds ReplayFrames from events; robot_position and target_position normalized from payloads. Telemetry is source of truth; replay is a view.
- **Event-driven decision trace** — Each telemetry event becomes one ReplayFrame; frames preserve chronological order; milestones (execution_started, waypoint_reached, path_computed, mission_completed, etc.) appear as frames. No continuous playback or frontend UI yet.
- **Replay foundation built from telemetry events** — Replay is a view over telemetry; no separate store. Sequence primary, timestamp secondary for ordering.
- **Decision-trace frames derived from mission telemetry** — ReplayFrame (index, event_type, source_component, timestamp, robot_position, target_position, payload) per event.
- **Replay API for reconstructing mission execution history** — GET `/missions/{mission_id}/replay` returns MissionReplay (mission_id, frame_count, frames); 404 if mission not found.
- **Scenario generation** — Deterministic generator produces N warehouse-like ScenarioConfigs (world_bounds, obstacles, target, robot_start); seed for reproducibility.
- **Benchmark execution foundation** — BenchmarkRunner runs full pipeline per scenario; BenchmarkService generates scenarios and runs benchmark; aggregate metrics (success_rate, average_waypoint_count, average_execution_steps) and per-scenario results.
- **Scenario-specific robot start positions** — Benchmark and orchestrator use robot_start_provider; execution spawns robot at scenario start; generator varies start pose per scenario.
- **Obstacle-inflated occupancy planning** — Grid build supports configurable inflation_radius (grid cells); tests can set 0 for tight tests; default adds safety margin.
- **Simplified waypoint generation** — A* path is simplified by collapsing collinear waypoints; NavigationResult exposes path_length_raw and path_length; benchmark results include path_length_raw per scenario.
- **Scenario-driven simulator world construction** — WorldLayoutSpec and build_world_from_config; SimulationEnvironment accepts optional world_layout; same layout drives planning and execution in benchmarks.
- **Aligned planning and execution geometry** — Benchmark runs use scenario bounds, obstacles, target, and robot start for both path planning and sim execution; single source of truth per scenario.

**Simulator architecture**

- **actions.py** — `RobotAction` enum (forward, backward, turn_left, turn_right, stop); used by `environment.step()` and the demo.
- **execution_engine.py** — WaypointExecutor: drives robot through waypoints (turn toward waypoint, forward until within tolerance); emits execution telemetry; ExecutionConfig (waypoint_tolerance, turn_threshold, max_steps_per_waypoint).
- **world_builder.py** — Builds a deterministic scene: default `build_world()` or scenario-driven `build_world_from_config(WorldLayoutSpec)`. Returns a `BuiltWorld`; `WorldLayoutSpec` carries bounds, obstacle_positions, obstacle_types, target_position (no PyBullet).
- **robot.py** — Kinematic robot (box body); maintains (x, y, theta) and syncs to PyBullet; exposes `forward`, `backward`, `turn_left`, `turn_right`, `stop` and `get_pose()`.
- **environment.py** — Connects to PyBullet (DIRECT or GUI). Optional `world_layout: WorldLayoutSpec` builds scenario world; otherwise default world. Exposes `reset()`, `step(RobotAction)`, `get_robot_pose()`, `get_world_bounds()`, `get_obstacles()`, `get_obstacle_types()`, `get_target_pose()`, `shutdown()`. No API or mission coupling.
- **grid_map.py** — Builds a 2D occupancy grid from world bounds and obstacle positions; configurable `inflation_radius` (grid cells); `world_to_grid`, `grid_to_world`, `is_blocked`, `neighbors` for path planning.
- **agents/navigation_agent.py** — A* path planning on an occupancy grid; collinear waypoint simplification; returns world-space waypoints with path_length and path_length_raw.
- **agents/perception_agent.py** — Rule-based perception from world metadata; returns `PerceptionResult` (targets, obstacles); swappable with YOLO later.
- **schemas/navigation.py** — Waypoint, NavigationRequest, NavigationResult.
- **schemas/perception.py** — DetectedObject, PerceptionRequest, PerceptionResult.

## Repository Structure

Run all commands from the repository root (the directory containing `backend/` and `scripts/`).

| Directory | Purpose |
|-----------|---------|
| `backend/` | Python package for the service and simulation. |
| `backend/api/` | FastAPI app, routes (missions, telemetry, replay, benchmarks), dependencies. |
| `backend/services/` | Business logic (mission lifecycle, orchestrator, orchestration, execution/sim run, telemetry, replay, benchmark). |
| `backend/schemas/` | Pydantic models (missions, execution, telemetry, replay, perception, navigation, benchmark). |
| `backend/scenarios/` | Scenario config, deterministic generator, benchmark runner. |
| `backend/simulator/` | PyBullet world, robot, environment, occupancy grid. |
| `backend/agents/` | Navigation agent (A*), perception agent (rule-based from world metadata). |
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

API base URL: `http://127.0.0.1:8000` (or the host/port you configure). Health: `GET /health`. Missions: `POST /missions`, `GET /missions/{mission_id}`. Execute: `POST /missions/{mission_id}/execute` (runs plan-perceive-navigate and waypoint execution in sim; returns summary). Telemetry: `GET /missions/{mission_id}/telemetry`. Replay: `GET /missions/{mission_id}/replay`. Benchmarks: `POST /benchmarks/run` (body: `benchmark_name`, `scenario_count`, optional `seed`; returns BenchmarkSummary).

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

**Execution demo**

```bash
python scripts/run_execution_demo.py
```

Creates a mission, runs the full pipeline (plan, perceive, navigate, waypoint execution in the simulator), and prints the execution summary and final robot position.

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

Mission API tests always run; simulator tests are skipped if PyBullet is not installed. Telemetry is in-memory and replaceable with SQLite later; it is the foundation for mission replay and benchmarking (replay and benchmark runs not implemented).

## Known Limitations

- Open-loop execution only; robot follows planned waypoints with no obstacle avoidance during motion.
- No dynamic obstacle handling; world is static at plan time.
- No replanning during movement; one plan per execute.
- Default mission path uses robot start (0, 0) unless a robot_start_provider is supplied (e.g. benchmark scenarios).
- Static world layout only for non-benchmark missions; single fixed warehouse layout, world_id not used.
- Planner is deterministic, not LLM-based yet; plan steps are keyword-derived.
- Static planning only; world is fixed at plan time.
- Path simplification is collinear-only (reduces straight-line noise); no curve fitting or smoothing.
- Perception: metadata-based detection only; no image-based perception yet; no tracking across frames.
- Telemetry is in-memory only; no persistence yet.
- Event-level replay only; one frame per telemetry event.
- No continuous playback or interpolation between frames.
- Replay depends on telemetry payload completeness (robot_position, target_position when payload includes them).
- No event filtering yet; replay returns all events as frames.
- Backlog: plan steps to become typed (structured); include target_x/target_y in execution event payloads so replay frames get target_position for UI; unified scenario adapter so planning layout and simulator WorldLayoutSpec derive from one conversion path (avoid drift between _layout_from_scenario and _world_layout_spec_from_scenario).

## Roadmap

- **Phase 1 — Core autonomy stack**  
  Connect mission API to the simulator; mission planning and execution loop; telemetry and basic replay/trace.

- **Phase 2 — YOLO perception integration**  
  Perception pipeline (e.g. OpenCV then YOLO) for object detection; feed observations into navigation and mission state.

- **Phase 3 — Reinforcement learning navigation**  
  Train or integrate policies for goal-directed navigation in the warehouse environment; optional LangGraph or similar for high-level control.

- **Phase 4 — Scenario benchmarking and evaluation**  
  Parameterized scenario generation; benchmark runs; metrics and evaluation for autonomy behavior.
