# AutonomyOS 2.0 CPU reference demo

Run from the repository root, Python 3.12:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt -r requirements-usd.txt
python -m pytest backend/tests -q
python -m scripts.run_evaluation_suite
python -m scripts.run_experiment --output artifacts/a --count 10 --seed 42
python -m scripts.run_experiment --output artifacts/b --count 10 --seed 42 --compare artifacts/a/report.json
python -m scripts.export_scenario_usd artifacts/warehouse.usda --seed 42
```

Use new output directories each time. Existing directories are rejected to preserve
run evidence. CLI exit status is nonzero on a failed evaluation or reproduction.
The gate is a configurable completion rate, not a safety certification.

Inspect `report.json` for results, simulator ticks per scenario, dependency versions,
source hash, seed, outcome hash, durations and explicit limitations. The legacy
`execution_steps` field retains its waypoint-record meaning for compatibility;
`simulator_steps` counts actual calls to the environment's step function.
`scenarios.json` records exact inputs; `mission-traces.json` contains decision and
waypoint events; `workflow.json` exports the durable SQLite workflow history.
Compare excludes timing, mission UUIDs and timestamps. Identical outcomes demonstrate
repeatability on this runtime; they do not establish cross-platform determinism.

To inspect state after restarting Python:

```python
from pathlib import Path
from backend.experiments.ledger import Ledger
state = Ledger(Path("artifacts/experiments.sqlite")).read("RUN_ID_FROM_REPORT")
```

Unexpected tool errors persist `failed` workflow state and are re-raised. A missing
simulator also fails evaluation even when the completion threshold is zero.
An interrupted process leaves its last stage visible; no automatic recovery is claimed.

## Optional inference boundary

`backend.integrations.nim.NimPlanner` accepts an explicitly configured HTTPS
OpenAI-compatible `/v1` base URL, model name and credential. It proposes only a
validated `ExperimentRequest`. Tests use `httpx.MockTransport` and establish protocol
behavior only. No live NVIDIA endpoint has been verified.
`require_approval` rejects approval hashes for changed proposals. This is a local
caller-side guard, not authentication or an enterprise approval system.

Never place credentials in source or reports. Model outputs cannot select arbitrary
Python functions, shell commands, endpoints or file destinations. A model may still
propose poor experiments; evaluation remains independent. Token/cost accounting,
model response provenance and live tool-use evals are pending before agent claims.

## OpenUSD boundary

The optional `usd-core` library writes and reopens an actual `.usda` stage.
Scenario obstacle geometry matches the scenario-built PyBullet world (1m cubes),
with robot/target geometry, starting robot yaw, bounds metadata, meters and Z-up.
The floor is visualization geometry. Physics schemas, articulation, materials,
Isaac Sim import/execution and Omniverse service connectivity are not implemented.

References:
- https://openusd.org/release/tut_xforms.html
- https://openusd.org/release/api/class_usd_geom_cube.html
- https://docs.nvidia.com/nim/large-language-models/latest/api-reference.html

## Delivery and operating limits

The Dockerfile is a CPU build recipe. Local Docker validation and remote GitHub
Actions execution must be recorded separately; a checked-in recipe is not deployment
experience. GPU Kubernetes/CoreWeave/Isaac/Cosmos validation requires appropriate
hardware, services and access. No deployment was performed.

Keep this as a local single-process tool. The upstream API has no authentication;
do not expose it publicly. SQLite is not a worker queue, and PyBullet clients are
not isolated for concurrent simulations. No distributed scalability claim is made.

## Local validation snapshot (2026-11-07)

57 tests passed with PyBullet and usd-core installed on macOS arm64 / Python 3.12.2.
Four hand-authored contract outcomes matched, including expected navigation failures.
Ten seeded scenarios (seed 42) completed in each of two runs; semantic hashes matched.
These are small local reference results, not evidence of general task accuracy or safety.
Docker CLI exists but its daemon is unavailable, so image build/run is unverified.
GitHub Actions is authored but has not run remotely. A FastAPI/Starlette httpx
compatibility deprecation warning remains in tests; no test was skipped.
OpenUSD emitted a native cache-line assumption warning on export but the round-trip
checks passed. No live NIM/Isaac/Cosmos/GPU services were used.

`requirements-macos-py312.lock` records the tested local dependency versions.
Use it on matching macOS/Python systems; it is not a portable Linux/GPU lockfile.

## PyTorch / Hugging Face GPU increment (prepared, not live validated)

The selected Runpod setup is a single L40S, the official PyTorch 2.8.0 / CUDA
12.8.1 / Ubuntu 24.04 image, and 150 GB temporary container disk. The dashboard
quoted $1.111/hour including disk on 2026-11-07. No persistent volume is selected.
The user's authorized ceiling for the first validation session is $100 total.
No paid resource was launched at preparation time; funding is still required.

The inference entry point is `python -m scripts.run_hf_validation --revision SHA`.
Install `requirements-inference.txt` in the GPU environment. Resolve and review a
full model commit SHA from Hugging Face before invoking it. The initial `nvidia/Nemotron-Mini-4B-Instruct` checkpoint was rejected because it
lacks safetensors weights. The selected candidate is
`nvidia/Llama-3.1-Nemotron-Nano-8B-v1`, with its model commit recorded at runtime.
The adapter disables remote Python code, requires safetensors and CUDA, and writes
raw output, token counts, latency, peak allocated VRAM and exact package/model
versions. It never executes the generated proposal. Schema validation tests pass;
model loading and actual GPU inference have not been verified.

Arm a four-hour stop using the pod-scoped Runpod CLI after confirming its installed
command syntax, then verify the timer process before starting lengthy downloads.
Export all evidence before stopping: temporary storage is erased. A container timer
alone is not a guaranteed billing cap; reconcile provider charges and confirm the
pod is stopped/removed in the console. Do not enable automatic credit replenishment.


### Verified cloud inference (2026-11-07)

The initial L40S became unavailable; the actual pod uses RTX 6000 Ada 48 GB,
62 GB host RAM, 16 vCPUs and 150 GB temporary disk, at $0.99 GPU + $0.021
disk per hour. PyTorch 2.8.0+cu128 / Python 3.12.3 sees CUDA on driver 595.91.07.
58 tests passed on the remote Linux host. A 100-scenario seed-42 PyBullet run
completed 99 cases; the expected contract suite matched 4/4 cases.

Hugging Face model `nvidia/Llama-3.1-Nemotron-Nano-8B-v1` at revision
`54641c1611fcff44fa4865626462445e0a153fc7` produced a valid structured
five-scenario proposal. Transformers 4.57.6, huggingface-hub 0.36.2 and
safetensors 0.8.0 were used. One invocation generated 38 tokens from 226 input
tokens in 1.093 seconds, with 16,126,129,664 peak allocated CUDA bytes.
Total loading plus generation was 32.562 seconds. These are one-request smoke
measurements, not throughput benchmarks or agent reliability statistics.
The generated proposal was not automatically executed. NIM is still unverified.
The rejected Mini checkpoint attempt remains in the evidence logs.


### Isaac Sim validation and evidence-transfer incident

Isaac Sim 6.2.0.0 was installed in a dedicated Python 3.12 environment on the
RTX 6000 Ada host. With the user's explicit EULA approval, the smoke script opened
the exported USD scene, applied collision/rigid-body schemas to a floor/probe and
advanced 120 steps. The observed final probe height was 0.09999999403953552 m;
`passed` was true. The default World physics configuration was used; GPU dynamics,
RTX sensor rendering and Isaac robot navigation were not tested. Startup emitted
nonfatal audio/UI/CUDA-ordinal warnings. A screenshot of the result is preserved.
The three live planning contract cases also reported 3/3 matches.

The evidence archive was created remotely, but the browser download call stalled
and did not deliver a verified local archive. The four-hour stop timer completed;
the first session used approximately $4.07 in credits and stopped billing. Because
all storage was temporary, raw logs and JSON reports were lost on stop. Restarting
the pod CPU-only confirmed that its workspace was empty except for a cache.
Do not represent the lost raw archive as delivered or the screenshot as a full
machine-readable evidence bundle. A repeat run must export and locally validate
its artifacts before cleanup; prefer dedicated retained artifact storage.

Cleanup confirmed after explicit user approval: recovery pod 23ckpo1x3djoxx is
stopped, compute/storage not running, total $0.00/hour; displayed balance $20.90.
