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

The mission API and simulator are not yet connected; mission execution and replay are not implemented.

## Repository Structure

Run all commands from the repository root (the directory containing `backend/` and `scripts/`).

| Directory | Purpose |
|-----------|---------|
| `backend/` | Python package for the service and simulation. |
| `backend/api/` | FastAPI app and HTTP routes. |
| `backend/services/` | Business logic (e.g. mission lifecycle). |
| `backend/schemas/` | Pydantic models for API and internal contracts. |
| `backend/simulator/` | PyBullet world, robot, and environment. |
| `backend/agents/` | Reserved for planning/perception agents (not yet implemented). |
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
python scripts/run_sim_demo.py
```

Uses PyBullet in DIRECT (headless) mode, runs a short sequence of movements, and prints robot and target poses. PyBullet can be difficult to install on some macOS setups; the demo and simulator tests are written to run where PyBullet is available.

**Tests**

```bash
python -m pytest backend/tests/ -v
```

Mission API tests always run; simulator tests are skipped if PyBullet is not installed.

## Roadmap

- **Phase 1 — Core autonomy stack**  
  Connect mission API to the simulator; mission planning and execution loop; telemetry and basic replay/trace.

- **Phase 2 — YOLO perception integration**  
  Perception pipeline (e.g. OpenCV then YOLO) for object detection; feed observations into navigation and mission state.

- **Phase 3 — Reinforcement learning navigation**  
  Train or integrate policies for goal-directed navigation in the warehouse environment; optional LangGraph or similar for high-level control.

- **Phase 4 — Scenario benchmarking and evaluation**  
  Parameterized scenario generation; benchmark runs; metrics and evaluation for autonomy behavior.
