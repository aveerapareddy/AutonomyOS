# Versioned engineering retrieval and bounded tuning

## Retrieval slice

`knowledge/engineering-v1.json` freezes eight first-party source documents with
source SHA-256, exact text and file/line citations. The index rejects stale source,
forged excerpts, invalid citation ranges and paths outside the repository. Fixed
BM25 lexical scoring returns extractive context. This is a retrieval foundation,
not embedding/vector search, semantic-model validation or LLM-generated RAG answers.
No external service, inference payment or GPU is required.

```sh
python -m scripts.query_engineering "How are concurrent SQLite event sequence numbers allocated?"
python -m scripts.evaluate_retrieval --output /new/retrieval.json
```

The transparent eight-query dataset has four development and four held-out queries;
all were written by the project implementer. Both sets achieved recall@3 = 1.0
and mean reciprocal rank = 1.0. This only validates a small smoke dataset. Fixed
parameters were not tuned after reading held-out results. Evaluation is performed
against every corpus document; the held-out split applies to questions, not documents.
No claim of independent expert labeling, enterprise scale or broad answer accuracy.
An unknown-token query returns no citations rather than fabricated context.

After an intentional source change, review the new source and regenerate the
versioned artifact with `python -m scripts.build_engineering_corpus`. Change the
version/dataset for substantive changes and retain previous evidence; silently
rebuilding a corpus would otherwise conceal staleness. Full-file retrieval is
suitable for this small source set; chunking and distractor-heavy evaluation remain
future work.

## Bounded controller-budget study

```sh
python -m scripts.run_tuning_study --output /new/tuning-study
```

`backend/experiments/tuning.py` freezes the protocol before execution: 4,000,
8,000 and 12,000 maximum steps per waypoint, 12 training scenarios at seed 101,
12 validation scenarios at seed 202, and 30 held-out scenarios at seed 303.
All other executor settings remain identical, including 0.15 waypoint tolerance.
The default API/mission behavior remains 8,000 steps; explicit configuration is
passed only for study runs. Simulator calls remain sequential.

Selection maximizes completions, then minimizes total simulator steps over all
cases, then the configured budget. Training produces a two-candidate shortlist;
validation chooses between those candidates. A selection-lock artifact containing
source provenance and hashes of protocol/results is written before any held-out
scenarios are generated or executed. Held-out evaluation compares only the locked
choice to the baseline, pairing outcomes by unique scenario ID. If selected equals
baseline, the same run is reused honestly rather than claimed as independent data.
Raw per-case failures, actual simulator ticks and telemetry are retained.

| Split | Budget | Completions | All-case simulator steps |
|---|---:|---:|---:|
| Training | 4,000 | 5/12 | 60,936 |
| Training | 8,000 | 10/12 | 81,879 |
| Training | 12,000 | 12/12 | 86,556 |
| Validation | 12,000 | 12/12 | 90,807 |
| Validation | 8,000 | 12/12 | 90,807 |
| Held out, baseline and selected | 8,000 | 28/30 | See raw report |

The selected budget is the existing 8,000. Held-out paired improvements,
regressions and simulator-step delta are all zero. **No improvement is claimed.**
The two held-out failures are preserved. Training gains for 12,000 did not justify
selection once validation tied it with the baseline.

This is procedural kinematic simulation, not collision safety, physical realism,
learned control or production tuning. A single seed per split and small sample do
not establish statistical generalization. Seeds and hashes make the study
reproducible; they do not make the sample representative. A new study/version is
needed before using these held-out outcomes for further development.

## Validation and remaining scope

Tests cover stale/forged citations, unsafe paths, missing relevance labels,
unknown queries, deterministic selection priorities, paired regression accounting
and a persisted selection gate before held-out execution. The real study separately
executes the full PyBullet mission pipeline. Raw artifacts include source hashes,
scenario manifests, configs, per-case summaries and telemetry.

Follow-on work: larger labeled retrieval datasets, chunked/semantic comparisons,
model-generated grounded answers with citation and hallucination evaluation,
actual NIM serving, richer Isaac robot/sensor tests, OpenTelemetry export and
container validation of the full integrated source. No resume claim should extend
beyond verified evidence. No cloud resources were started for this phase.
