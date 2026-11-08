# AutonomyOS 2.0: evidence-first simulation automation

> Historical phase record. See [current delivery status](COMPLETION.md) and [runbook](RUNBOOK.md) for subsequent implementation and evidence.

> Current status: the second GPU run was saved and independently verified before shutdown.
> The governed workflow is implemented and the integrated backend passes 135 tests.
> See [the current validation record](VALIDATION_RERUN.md); older snapshots below are historical.

## Audit and provenance

Audited upstream commit `8da6b73cac470d6280b4369038a6346e96ff4e48` on 2026-11-07.
Sources: https://github.com/aveerapareddy/AutonomyOS and target requisition
https://careers.caterpillar.com/en/jobs/r0000404257/principal-software-engineer-agentic-ai-simulation-automation/ .
The official posting was initially inaccessible to web search. It was subsequently read
from the user's open employer browser tab on 2026-11-07; the requirements below match
the official page. The initial secondary reference was
https://emploive.com/jobs/9570004/principal-software-engineer-agentic-ai-simulation-automation-caterpillar-inc .
The earlier chat's fit score and personal experience claims are not evidence.

Existing code implements FastAPI missions, metadata perception, A* navigation,
kinematic waypoint execution in PyBullet, seeded scenario generation, in-memory
telemetry, event replay, and benchmark aggregation. This is a small simulation
prototype, not high-fidelity robotics or a production agent system.

Audit findings:
- Rule-derived plan strings do not control tool selection; no foundation model is used.
- Mission and telemetry state disappear on restart; no experiment provenance bundle.
- Benchmark `execution_steps` counts waypoint records, not simulator ticks.
- Simulator robot teleports its body by kinematic pose updates. No collision safety
  claim follows from successful execution or occupancy-grid inflation.
- PyBullet calls use the default client: retain sequential runs until client isolation exists.
- Scenario target rejection sampling has no attempt bound; do not accept arbitrary bounds yet.
- README contains stale statements saying implemented replay/benchmark features are absent.
- Dependencies use lower bounds; no CI, container recipe, GPU deployment or NVIDIA implementation.

## Phased architecture and acceptance gates

Preserve the existing mission API and engine. Add an experiment control plane above them:

`typed experiment -> policy gate -> scenario tool -> simulation tool -> evaluator -> report`

Each stage produces durable state/events, input hashes, outcomes and elapsed time.
A seeded scenario manifest is the source of truth; evaluation compares semantic
results, excluding UUIDs, timestamps and wall-clock timing. Every run carries its
runtime/dependency/source provenance. Tool failures must fail closed, never become passes.

1. **CPU reference slice (this increment).** Bounded typed experiment requests,
   deterministic role/stage orchestration, SQLite workflow/audit history, real PyBullet
   runs, explicit task-completion evaluation, reproducible report and replay comparison.
   Gate: baseline tests plus positive, negative and restart/reproducibility tests.
   This is deterministic workflow orchestration, not autonomous multi-LLM agents.
2. **Agent decision layer.** Typed tool proposals from a model behind an inference
   protocol; simulation/evaluation tools remain authoritative. Persist approval of
   exact proposal hashes, model/provider/version, tool arguments, token usage and cost
   when measured. Add adversarial prompts, malformed outputs, budget exhaustion,
   timeout/retry and approval bypass evals. No arbitrary code/shell tools. Gate:
   recorded live inference plus tool-use evals; mocks demonstrate contracts only.
3. **Engineering knowledge and tuning.** Cited retrieval over versioned local engineering
   docs; compare retrieval quality on a labeled corpus. Bounded parameter search on
   training seeds, selection on validation seeds and final held-out evaluation.
   Report paired regressions and failures; never claim improvement from training data.
4. **NVIDIA interchange and inference.** OpenUSD export with meters/Z-up, explicit
   geometry and identity, round-trip checks using `usd-core`. NIM/Nemotron adapter
   exercised against an actual configured endpoint. Isaac Sim headless import and
   simulation smoke test on supported hardware. Gate: exact SDK/model versions,
   input assets, logs and measured outcomes. OpenUSD alone is not Isaac integration.
   Cosmos augmentation requires model access, GPU resources and evaluation of generated
   scenarios; it is separate from seeded procedural generation.
5. **Scale and presentation.** Queue workers with isolated simulator clients,
   cancellation and idempotency; authenticated API/UI; OpenTelemetry exporter;
   Docker and Kubernetes CPU/GPU profiles, resource quotas, secret injection.
   Validate containers locally, then GPU deployment on a real cluster before claiming
   CoreWeave/Kubernetes operations. Load tests, threat model, operational runbook,
   architecture decisions and failure demos accompany a recorded walkthrough.
6. **Resume gate.** After all intended project scope is validated, extract only measured
   portfolio accomplishments and request the user's actual employment/education history.
   A portfolio cannot establish years of experience, team leadership or production adoption.

## Gap matrix

| Requirement theme | Upstream evidence | Planned evidence / remaining gap |
|---|---|---|
| Python/API/engineering simulation | FastAPI, A*, PyBullet code | CPU tests and real experiment reports; no physical fidelity claim |
| Agent orchestration, tools, state | Fixed rule pipeline | Durable staged workflow first; model decisions and multi-agent reasoning remain phase 2 |
| Scenario/experiment automation | Seeded generator, benchmark runner | Manifest hashes, replay comparisons, evaluation gate |
| Evals: completion/reliability/reproducibility | Success aggregates | Per-case results, expected failures, repeat runs; no accuracy dataset yet |
| Latency/cost/safety | No measured contract | Stage latency; cost unknown without model; collision safety explicitly unevaluated |
| Observability/audit/governance | In-memory mission events | SQLite events and exported traces; approvals and OTel later |
| NIM/NeMo/Nemotron | None | Live inference evidence required; not implemented |
| Omniverse/Isaac/OpenUSD | None | Real OpenUSD round trip and GPU Isaac import required |
| Cosmos/multimodal/world models | None | Hardware/model-dependent follow-on; no substitute claim |
| RAG/vector/semantic models | None | Versioned corpus and retrieval evals, phase 3 |
| Containers/CI/Kubernetes/GPU cloud | None | CPU CI first; deployment evidence only after execution |
| Principal leadership | No evidence in repository | ADRs/runbooks demonstrate design communication, not employment leadership |

## Design decisions

Use SQLite for a single-process local experiment ledger, not a distributed queue.
Keep simulation sequential because the upstream PyBullet default client is shared.
Keep the experiment module independent from mission API global state.
Use a deterministic workflow initially to establish a trustworthy measurement tool
before allowing models to propose actions. Reports explicitly list unevaluated dimensions.
Do not silently replace unavailable GPU services with a mock bearing the same name.

## Delivered first increment

The CPU reference slice is implemented and locally validated. Actual simulator-step
counts now complement the legacy waypoint-record field. A blocked start/goal same-cell
shortcut was fixed using a negative regression case. Optional OpenUSD geometry export
is implemented and round-trip tested with usd-core 26.11. NIM structured proposals and
exact-proposal approval have mock protocol tests only; live inference is unverified.
The CI workflow and CPU Docker recipe are authored, not deployed. See DEMO.md for
commands, evidence boundaries and the local validation snapshot. Phases 2–5 remain
follow-on work; the overall production-style platform is not complete. Resume work
remains deferred until the intended project scope and external validation gates finish.


## Live validation update

PyTorch/Hugging Face Nemotron inference and an Isaac Sim geometry/physics smoke
check were observed on a paid RTX 6000 Ada host. See DEMO.md for measured results,
scope limits and the evidence-transfer failure. This advances the NVIDIA ecosystem
gap beyond protocol-only tests, but NIM serving, Isaac navigation, Cosmos and cloud
orchestration remain incomplete. The first run lost its raw archive; the second run now has a complete independently verified local archive; see VALIDATION_RERUN.md.


## Updated gap matrix after the rerun and integration

| Requirement | Verified evidence | Remaining work |
|---|---|---|
| Agent orchestration | Real model proposal; bounded typed tool; durable exact-digest review; negative gates and cached result | Multi-agent reasoning and authenticated approval |
| Simulation automation/evals | Seeded experiments, repeat hashes, 99/100 baseline retained, 135 combined tests | Held-out tuning study and richer task metrics |
| Observability | Mission and workflow SQLite journals, ordered raw events, provenance and artifact integrity | OpenTelemetry collector/exporter and operational dashboards |
| NVIDIA/PyTorch/HF | Pinned Nemotron inference on RTX; USD import and Isaac CPU-physics smoke | NIM endpoint, NeMo, Cosmos, Isaac robot/sensor workloads |
| Reproducibility | Exact GPU source and 35-file archive verified before shutdown; governed CPU demo | Full merged-source GPU rerun only if later changes require it |
| UI/delivery | Integrated phase-2-ai dashboard and CPU deployment recipe | This local merge is not pushed/deployed; no live URL claimed |
| RAG/tuning | Not implemented | Versioned corpus, labeled retrieval evaluation, train/validation/held-out seeds |

Next planned increment is versioned engineering retrieval and held-out parameter
search. Approval/authentication, distributed scheduling and production deployment
remain separate gates. A resume cannot yet claim the full planned scope.

## Phase 3 delivered slice

Versioned first-party engineering retrieval now has exact hash-checked citations
and a transparent eight-query evaluation (recall@3 and MRR both 1.0 on each small
four-query split). This is lexical extractive retrieval, not full generative RAG.
A bounded three-budget study uses separate seeds for training, validation and held
out; selection is persisted before held-out evaluation. It selected the existing
8,000-step baseline and achieved 28/30 held-out completions with zero paired change.
No tuning improvement is claimed. See KNOWLEDGE_AND_TUNING.md for the fixed protocol,
all results and the remaining gaps. Resume preparation remains deferred.
