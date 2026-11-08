# Operator workspace and incremental telemetry

> Historical phase record. See [current delivery status](COMPLETION.md) and [runbook](RUNBOOK.md) for subsequent implementation and evidence.

This increment connects the Angular dashboard to the durable experiment controller.
The original visual reference is unavailable; no visual-parity claim is made. The
existing industrial 3D/2D viewer is preserved. This is local development, not a
public deployment or a production identity system.

## Run locally

Build the dashboard following docs/engineering/DEPLOYMENT.md. Configure these
server settings before starting a **single** API worker on loopback:

- `AUTONOMY_FRONTEND_DIRECTORY=frontend/autonomy-dashboard/dist/autonomy-dashboard/browser`
- `AUTONOMY_DATABASE_PATH=data/missions.sqlite3`
- `AUTONOMY_WORKFLOW_DIRECTORY=data/workflows`
- `AUTONOMY_OPERATOR_TOKEN`: a private random token of at least 24 characters,
  supplied through the environment, never committed or embedded in frontend assets.
- `AUTONOMY_PLANNER_MODE=rule_based` for the CPU mission demo.

Operator workflows are disabled unless the directory and token are configured.
`AUTONOMY_PUBLIC_DEMO=true` blocks every operator route, including reads. Keep the
operator interface on loopback; any future remote use needs HTTPS, per-user
identity, roles, quotas and deployment review. A shared token grants all operator
functions; reviewer labels are self-declared and do not attest individual identity.
The browser holds the token only in component memory. No localStorage persistence.

## Review a saved model proposal

1. Enter the operator token and load history, or import a saved inference JSON file.
   Pasting report JSON is also supported when browser upload permissions are absent.
2. Inspect model revision, scenario count, seed, success threshold and approval digest.
3. Enter a reviewer label and approve the exact request, or reject with a reason.
4. Execute an approved request; inspect completion/failure, outcome metrics and the
   ordered audit timeline. Refresh recovers persisted state; export saves JSON evidence.

This does not make a new inference call. Imported model metadata is independently
revalidated against the raw model output but is not cryptographically provider-attested.
The API policy caps each proposal at 10 scenarios, one fixed tool call and a
60-second tool timeout. It preserves the existing exact-digest review gate and
at-most-once automatic dispatch behavior. Failed/running tools are not silently retried.

Routes: `GET /workflows`, `POST /workflows/import`, `GET /workflows/{id}`,
`POST /workflows/{id}/approve`, `/reject` and `/execute`. Use an Authorization bearer
token on every route. Imports are streamed with a 256 KB limit; clients cannot
choose server filesystem paths. The local operator must manage retention: there
is not yet a cumulative disk quota or complete role/rate-limit service.

## Live state and replay

The dashboard polls ordered telemetry every 250 ms while its mission executes,
using `after_sequence` as a reconnect cursor and deduplicating event sequences.
`scene_ready` includes simulator-world geometry and planned waypoints before
execution finishes. Robot-state events come from actual PyBullet poses. Final
results remain authoritative; this is incremental HTTP polling, not SSE/WebSocket
streaming or wall-clock real-time physics. Fast runs can finish between polls.

New robot-state and terminal execution events carry simulation time derived from
the configured simulator timestep. Replay schedules event transitions using those
time differences, with pause, scrub and result controls. Older traces without
simulation-time fields have no timing guarantee. Playback does not interpolate
poses between sampled frames and browser scheduling can introduce timing drift.

API mission, benchmark and workflow execution share a nonblocking process-level
gate because the current PyBullet implementation uses a shared default client.
An overlapping call returns 409 (the public-demo middleware can return 429 first).
This is not distributed-worker isolation: run one worker; queueing remains future work.
The gate does not coordinate independent CLI processes.

## Verification

- 150 backend tests passed, zero skipped; one upstream httpx deprecation warning.
- Tests exercise token denial, public-mode denial, oversize/invalid imports,
  exact-digest approval, rejected/unapproved execution, real execution and cached result.
- A concurrent API test pauses a real simulator at its first step and verifies that
  scene metadata can be fetched before execution completes, then checks incremental
  robot-state retrieval and the final simulation clock after release.
- Production Angular build passed. Browser checks completed a real mission with
  203 events, rendered the 3D scene, exercised replay controls and inspected the
  persisted real Nemotron proposal. Automated tests use explicitly test reviewer
  labels; the preserved real proposal remains awaiting human review.
- File-chooser upload hit an extension permission limitation; the API import is tested
  separately and the paste-JSON path was browser-verified with the preserved real report.
- `knowledge/engineering-v2.json` is a reviewed new source snapshot for changed
  execution/workflow code. The v1 snapshot and previous delivered evidence remain intact.

Remaining gates: original-reference visual matching, responsive/browser coverage,
public deployment of the integrated source, individual identity/RBAC, distributed
execution, live NIM and richer Isaac workloads. No new GPU runtime was started.
