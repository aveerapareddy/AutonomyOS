# AutonomyOS 2.0 — Requirements Traceability

Status: incrementally implemented. See ../OPERATOR_DASHBOARD.md, ../VALIDATION_RERUN.md
and ../KNOWLEDGE_AND_TUNING.md for current integrated evidence; older baseline notes
are historical. Do not interpret planned items as implemented.

## Current implementation (phase-2-ai)
- Angular 21 dashboard with mission creation, execution summary, telemetry and top-down canvas.
- FastAPI mission APIs, PyBullet simulation, A* navigation and waypoint execution.
- LLM planner with deterministic fallback; metadata and optional YOLO perception paths.
- Scenario generation, benchmarking, replay and Python regression tests.

## Required delivery gates

| ID | Requirement | Verification gate | Status |
|---|---|---|---|
| A01 | Preserve existing mission workflows | Python regression tests and Angular production build | Passed baseline CI; regression checks continue |
| A02 | Interactive 3D digital twin | Browser E2E robot inspection and real simulator-state replay | Partial: 3D projection and recorded pose replay verified; original reference parity pending |
| A03 | Real-time telemetry | Ordered events, reconnection and replay tests | Partial: incremental in-flight HTTP polling, geometry/pose telemetry, cursor reconnect and simulation-clock replay; SSE/WebSocket pending |
| A04 | Durable agent orchestration | Workflow checkpoint/restart and tool execution tests | Bounded single-tool workflow, restart, caching and API tests passed; distributed recovery pending |
| A05 | Human approval and guardrails | Authorization and adversarial tool-call tests | Exact-digest review, negative gates and operator token tested; individual identity/RBAC pending |
| A06 | Distributed simulation runs | Queue, retry, idempotency, cancellation and failure tests | Planned |
| A07 | Map-to-simulation | Map import with validated geometry and reproducible output | Planned |
| A08 | Site-to-simulation | Asset and site data mapped to scene entities | Planned |
| A09 | OpenUSD | USD scene export, validation and import | Planned |
| A10 | Isaac Sim | Real GPU simulation execution and telemetry capture | Planned |
| A11 | Omniverse interoperability | Verified scene workflow and compatibility record | Planned |
| A12 | NVIDIA NIM | Live inference request and integration tests | Planned |
| A13 | NeMo and Nemotron | Measured model evaluation and agent integration | Planned |
| A14 | Cosmos | Reproducible world-model scenario experiment | Planned |
| A15 | Newton | Physics integration or explicit evidence-based feasibility finding | Planned |
| A16 | CUDA and GPU operations | GPU execution, profiling and performance evidence | Planned |
| A17 | Multimodal AI | Image/scene evaluation against ground truth | Planned |
| A18 | Engineering RAG | Retrieval-grounded answers with citation and regression checks | Planned |
| A19 | Knowledge graph | Asset, scenario and failure relationships with query tests | Planned |
| A20 | Evaluation platform | Accuracy, reliability, latency, safety, cost and reproducibility metrics | Planned |
| A21 | Production engineering | CI/CD, observability, security, infrastructure as code and runbooks | Partial: regression/build CI, request tracing, demo policy and deployment package; full production gates pending |
| A22 | Public hosted demo | HTTPS deployment and full end-to-end smoke test | Planned |

## Engineering rules
- Extend existing Angular and Python modules before adding replacements.
- Never label a mock, adapter scaffold or prerecorded trace as a live integration.
- Simulation state is authoritative; UI is a projection of recorded or streamed state.
- Keep the public demo functional without permanent GPU allocation.
- Publish benchmarks only with reproducible inputs and execution artifacts.
- Prepare role-targeted resume only after demonstrated implementation.
