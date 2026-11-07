# GPU validation and local evidence gate

The runner is `python -m scripts.cloud_validate`. It captures subprocess stdout and
stderr separately for preflight, dependency installation, tests, simulation contract
cases, two 100-scenario seed-42 experiments, USD export, pinned Nemotron inference,
three labeled planning contracts, isolated Isaac installation, the 120-step Isaac
smoke test and both Python environment snapshots. Every subprocess has a timeout.
After each stage, it writes session state and an archive with a file-size/SHA-256
manifest. Errors produce failed evidence rather than passes.

Use an RTX-capable GPU with at least 40 GB VRAM for the combined reference setup.
The tested container is `runpod/pytorch:1.5.0-cu1281-torch280-ubuntu2404`; the pinned
model and revision are in `scripts/cloud_validate.py`. Install Isaac separately from
the inference environment. The EULA flag requires the operator's prior acceptance;
the script does not infer license consent.

```sh
python -u -m scripts.cloud_validate \
  --evidence /workspace/gpu-rerun \
  --isaac-env /workspace/isaac-env \
  --accept-isaac-eula
```

The selected output directory must be new. Keep secrets, provider credentials and
model access tokens outside the source/evidence directories. Public model weights
remain in the model cache; the evidence records their pinned revision and runtime.
No secret or model cache is intended to be packaged.

The final files are `/workspace/gpu-rerun.zip` and
`/workspace/gpu-rerun.transfer.txt`. The latter is a JSON envelope containing an
archive checksum and base64 bytes, suitable for transport through an authenticated
notebook text view. In browser automation, read raw displayed text in 64,000-character
chunks; larger single reads may be truncated by the client. Reconstruct bytes locally
and check the envelope's SHA-256 before invoking the independent archive verifier.
This path avoids the previously stalled browser-download event. A transport preflight
must pass against the actual host before installing large GPU dependencies.

After the runner exits, copy its console transcript and the watchdog transcript into
the evidence directory and rebuild the bundle with `bundle_evidence`. Do this before
performing final local verification so that every captured transcript is included.

```sh
python -m scripts.verify_cloud_evidence /local/path/gpu-rerun.zip \
  --extract-to /local/path/verified-gpu-rerun
```

Successful verification writes `LOCAL_RECEIPT.json` containing the archive SHA-256,
verified file count and `all_validation_gates_passed: true`. It independently checks
archive paths, duplicate members, decompressed size, all file hashes/sizes, required
raw logs, session stage exit codes, JUnit failures/errors/skips, model identity,
planning contract completion, simulation gates and repeatability, and the Isaac
result against the exported stage hash. A partial bundle never authorizes shutdown.
The manifest proves content integrity, not an independently signed remote attestation.

Only after that receipt exists should the operator stop the rented host. A budget
watchdog is an emergency fallback and does not replace export verification. All
intended stops must follow the user's evidence-retention instruction. Check the
provider shows zero compute/storage charge after stopping an ephemeral-only pod.

Scope: the Isaac check is geometry interchange and a falling-body physics smoke
test on an RTX host. Default CPU physics is used; robot navigation, GPU dynamics,
RTX sensor rendering, NIM serving, Cosmos and Kubernetes are not validated by it.
The three planning prompts are a small labeled contract set, not a production
agent-reliability evaluation.
