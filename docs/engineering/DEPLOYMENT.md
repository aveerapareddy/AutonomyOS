# CPU demo deployment runbook

The Angular dashboard is served by FastAPI at `/demo/`; the API remains at `/missions`, `/health` and related existing routes. Production browser requests use the same origin. No deployment URL is recorded until an actual HTTPS endpoint passes the smoke test.

## Build and run

```sh
docker build -t autonomyos-demo .
docker run --name autonomyos-demo -p 127.0.0.1:8000:8000 \
  --mount source=autonomyos-data,target=/data autonomyos-demo
python scripts/smoke_demo.py --mission-file work/demo-mission.txt
docker restart autonomyos-demo
python scripts/smoke_demo.py --mission-file work/demo-mission.txt --verify-restart
```

The image uses one non-root Python 3.11 process, pinned CPU dependencies, deterministic rule-based planning and metadata perception. It requires neither a GPU nor an inference API key. The Docker build uses the published x86-64 PyBullet wheel; ARM Linux may require a compiler/source build and is not validated by the hosted CI job.

## Hosting requirements

- Route HTTPS to container port 8000. Enforce a 16 KiB request body limit and a request timeout that allows the bounded simulator run. Do not publish development servers.
- Mount persistent writable storage at `/data`; back up the SQLite database with its backup API or while stopped. A container restart retains its writable layer, while replacement requires the persistent volume.
- Use exactly one application worker for this demo. The creation throttle and simulation lock are process-local, not a distributed quota system.
- Set no paid inference credentials in the anonymous demo. The deterministic planner is intentional and must remain labelled `rule_based`.
- The public-demo flag disables batch benchmarks, limits mission creation to 20 requests/minute globally, and allows one execution request at a time. Mission text is limited to 4,000 characters. Declared request length is checked in-app; the gateway must enforce actual body length, including chunked requests.
- Request IDs, status, method and duration are logged without mission text or credentials. Request tracing and security headers are a baseline, not a complete production observability/security platform.
- The anonymous demo has no private user accounts or access isolation. Do not enter confidential or personal mission data. Configure retention and storage monitoring before sustained hosting.

## Verification and release gates

CI runs backend regression tests, a clean Angular installation/build, a production dependency audit and a real container smoke test. The smoke test checks asset delivery, mission creation, completed PyBullet execution, sampled telemetry, ordered event sequences, replay, cursor reconnect and persistence after restart. It must also pass against the actual HTTPS deployment before that endpoint is advertised.

At the current increment, recorded playback runs at 10 events/second and is labelled recorded replay. It is not a real-time physics stream. Durable mission/event storage does not implement workflow checkpoint/resume or distributed scheduling.

GPU validation and NVIDIA integration evidence are being developed separately. Incorporate verified artifacts and reconcile branch changes before claiming the complete portfolio roadmap is delivered.
