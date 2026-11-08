# GPU rerun and governed workflow validation

## Verified GPU rerun

The second validation session used Runpod pod `tq3qlzwmtge6cr`, RTX 6000 Ada
48 GB, official PyTorch 2.8.0 CUDA 12.8 image. All 13 stages exited zero.
The local archive SHA-256 is
`63df0338add57628cc4421a8510d30d657960ce0afecb07d29913dce2367090a`.
The independent verifier checked 35 files, their hashes/sizes, raw logs, source,
JUnit and result gates. Transfer and verification completed before shutdown.
Both this pod and the recovery pod were then observed stopped at $0.00/hour.

- GPU-source backend tests: **65 passed**, no skips/failures.
- Two seed-42 100-scenario experiments: **99/100** each, exact source/scenario/
  semantic-outcome reproduction. The one failure is retained in the reports.
- Four positive/negative navigation contract cases passed.
- Hugging Face model `nvidia/Llama-3.1-Nemotron-Nano-8B-v1`, revision
  `54641c1611fcff44fa4865626462445e0a153fc7`, loaded via PyTorch/Transformers.
  Structured proposal generation: 226 input tokens, 38 output tokens,
  1.272486 seconds, peak allocated CUDA memory 16,126,129,664 bytes.
- Three labeled live planning prompts matched expected structured requests.
- Isaac Sim 6.2.0.0 imported the exported USD and executed 120 physics steps.
  Probe height moved from 1.5 to approximately 0.1. Default CPU physics on an
  RTX host: no claim of GPU dynamics, robot navigation or RTX sensor validation.

The archive includes exact pre-integration source, stage logs, environment freezes,
JSON reports, JUnit, SQLite history, traces and USD. This GPU result applies to that
source snapshot, not automatically to every later change. NIM serving, Cosmos,
Kubernetes and CoreWeave remain unvalidated. The first session's lost raw archive
is historical; its screenshot is not used as a substitute for the rerun evidence.

## Next phase: governed model-to-tool workflow

After GPU shutdown, the local experiment increment was merged with upstream
`phase-2-ai` commit `3f5aa73`, retaining the dashboard and durable mission journal.
The new workflow consumes the preserved live model proposal without rerenting a
GPU. It records policy/proposal hashes, model revision, review identity/type,
ordered events, and a bounded simulator tool execution in SQLite.

The final CPU demo passed: default human-review policy blocks automated review,
unapproved execution and a wrong approval digest are rejected, approval survives
controller reconstruction, one real five-scenario simulation completes, and a
second execution returns the recorded result without another tool call. The demo
uses a separate automated-validation policy and claims no human approval.

Two additional integrated-source seed-42 100-scenario runs each scored 99/100
and reproduced exact scenario/source/outcome hashes.

Combined backend validation: **135 passed**, zero skipped, one upstream Starlette
httpx deprecation warning. Clean frontend dependency installation and the Angular
production build also passed locally. A restart regression also verifies durable telemetry
export includes events written by a previous service instance.

The workflow offers at-most-once automatic dispatch, not distributed exactly-once
execution. A crash while running requires operator investigation; retries are not
silently issued. CLI identity is trusted locally; authentication and multi-user
approval remain future work. Imported model token counts are report metadata,
not independent billing telemetry. See AGENT_WORKFLOW.md for commands and limits.

## Reproduce

```sh
python -m pytest backend/tests -q
python -m scripts.verify_cloud_evidence /path/GPU-validation-rerun.zip --extract-to /new/verification-directory
python -m scripts.run_governed_demo --inference /path/GPU-validation-rerun/inference.json --output /new/governed-demo
```

Root Dockerfile is the integrated dashboard/API CPU app. The separate experiment
CLI recipe is `deploy/experiments.Dockerfile` (`docker build -f
 deploy/experiments.Dockerfile .`); that moved recipe has not been built locally.
GPU reruns use GPU_VALIDATION.md. Resume preparation remains deferred until the
intended scope is implemented and validated and actual career history is supplied.
