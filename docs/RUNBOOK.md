# Reproduce, operate and review

## CPU reference

Use Python 3.11 and Node 20. Install `backend/requirements-demo.txt` and `requirements-observability.txt`; add `requirements-usd.txt` for USD checks and `requirements-agents.txt` for LangGraph. Run `python -m pytest backend/tests -q`. From `frontend/autonomy-dashboard`, run `npm ci` and `npm run build`.

Set `AUTONOMY_FRONTEND_DIRECTORY=frontend/autonomy-dashboard/dist/autonomy-dashboard/browser`, `AUTONOMY_PLANNER_MODE=rule_based`, an operator token, and persistent mission/workflow/operations/trace directories. Start `uvicorn backend.api.main:app --host 127.0.0.1 --port 8000`. In a separate process run `python -m scripts.job_worker --root <the same operations directory>`. Visit `/demo/`.

Use a fresh output directory with `python -m scripts.validate_completion --output <new-directory>`. The script executes real seeded simulations, verifies site dimensions through USD, checks input idempotency and exports source-grounded answers. `python -m scripts.smoke_operations --url http://127.0.0.1:8000 --output <new-directory>` checks the authenticated HTTP/worker path; it reads the operator token from the environment.

For Docker, configure a token outside version control and run `docker compose -p autonomyos -f deploy/compose.yaml up --build`. The API binds loopback port 8013; the worker has no network service. Back up the evidence volume before `down`; avoid `down -v` until the backup has been verified. Runtime images are nonroot, read-only, capability-dropped and resource-bounded. ARM64 requires the native image override used in `deploy/kubernetes/native-arm64`.

For Kubernetes, use an isolated test context, create the documented operator secret privately, and apply `deploy/kubernetes`. The native ARM64 overlay is for the locally validated Kind image. Load the image into Kind first. The single API/worker replicas share a PVC; Recreate avoids quota-blocked rolling updates. This is not a distributed broker or high-availability configuration. Use loopback port-forwarding; no public ingress is provided.

## Optional model environments

Keep semantic, Newton and Isaac packages in separate virtual environments to prevent conflicting scientific/simulator dependencies. `requirements-semantic.txt` pins PyTorch/Transformers/safetensors. Run the help for `scripts.semantic_retrieval`, `scripts.evaluate_semantic`, and `scripts.evaluate_grounded_answers` to build a fresh index and write evaluation artifacts. Configure `AUTONOMY_SEMANTIC_PYTHON` and `AUTONOMY_SEMANTIC_INDEX` only after the index source hashes pass. Model downloads require network access; runtime remote code is disabled. Semantic requests are single-concurrency with a 30-second timeout.

`python -m scripts.newton_smoke --help` describes the CPU contact smoke. Isaac requires supported NVIDIA hardware, official packages and separately accepted Omniverse terms. `scripts.cloud_isaac_robot` creates its own Python 3.12 environment and pins Isaac 6.2 plus a compatible Pillow; do not install the CPU vision Pillow 13 pin into Isaac. Its bounded official Jetbot lane/RTX test must pass its own report before being advertised. A live NIM endpoint and gated Cosmos license/access are separate prerequisites, not interchangeable with Hugging Face Nemotron inference.

## Demonstration sequence

1. Create a red-target mission, execute it, inspect the live 3D scene and event stream. Scrub recorded events and use simulation-time playback; switch to the 2D map.
2. Connect the private workbench, queue a small seeded experiment, inspect successes/failures and export the actual job.
3. Validate the metric transfer-lane site. Load the blocked-route example, run it, and inspect its failed evaluation instead of a green completion.
4. Ask a supported engineering question and inspect exact quotes/hashes; ask an unknown query and observe abstention. Compare optional semantic context without claiming new inference-generated answers.
5. Select evidence-graph nodes to inspect persisted relationships. Show request metrics and local trace records.
6. Import a real saved model record with its revision, prepare a proposal, inspect its exact digest and review journal. A default LangGraph run pauses for independent review; execution cannot self-approve.

## Threat model and failure handling

The private workbench assumes a trusted local operator and bounded synthetic inputs. Role checks protect reads/reviews/execution/management. Public-demo mode denies all operations and review routes and accepts only bounded synthetic missions; never expose a private token-configured workbench without an appropriate network/authentication deployment. Shared-token mode cannot distinguish people. Hashes establish artifact integrity, not external identity or correctness.

Untrusted model output is data: strict schemas and limits reject malformed/oversized requests; no shell, path or arbitrary-code tool is exposed. Unknown/stale engineering sources fail closed. The site importer checks units, finite bounds, obstacle dimensions and start/target geometry; it does not certify real facilities. Source-quoted answers are context, not approved engineering decisions.

A queued job can be canceled. A lost worker heartbeat marks an interrupted job terminal; submit an explicitly new key to rerun after inspecting evidence. Restart APIs against the same persistent directories. At-most-once dispatch is scoped to the local workflow ledger, not a globally distributed exactly-once guarantee. Simulator success does not establish contact safety; the PyBullet robot is kinematic.

For paid validation: set a budget and timed stop guard before work; preserve controller logs, failed attempts, stdout/stderr, source archives, dependency freezes, reports, database backups and sensor frames. Package with `scripts.package_cpu_evidence`, transfer locally, verify SHA/manifest and run `scripts.verify_cpu_evidence` (or `verify_cloud_evidence` for the original GPU format). Independently inspect advanced robot reports and image hashes. Only then stop the pod. A stop guard is a backup, not a substitute for verifying the final cloud status and billing rate. Temporary pod disks are disposable after the receipt is verified.
