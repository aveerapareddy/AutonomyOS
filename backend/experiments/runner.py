"""Sequential typed tool workflow over the existing real simulator engine."""
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import time
import uuid
from pathlib import Path

from backend.experiments.ledger import Ledger
from backend.experiments.models import ExperimentReport, ExperimentRequest
from backend.scenarios.benchmark_runner import run_benchmark
from backend.scenarios.generator import generate_scenarios
from backend.services.mission_service import MissionService
from backend.services.telemetry_service import TelemetryService

ROOT = Path(__file__).resolve().parents[2]
LIMITATIONS = [
    "Deterministic role workflow; no LLM or autonomous multi-agent reasoning.",
    "Kinematic PyBullet model; collision safety and physical accuracy are unevaluated.",
    "execution_steps is waypoint records, not simulator ticks.",
    "No inference calls; model cost is unmeasured, not a measured zero.",
    "No Isaac Sim, NIM, Cosmos, Kubernetes or GPU execution in this run.",
    "SQLite is a local ledger; interrupted runs are inspectable, not automatically resumed.",
]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def provenance():
    def git(*args):
        return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()
    try:
        revision, dirty = git("rev-parse", "HEAD"), bool(git("status", "--porcelain"))
    except (OSError, subprocess.CalledProcessError):
        revision, dirty = "unavailable", True
    # Hash source as well: a dirty revision alone cannot identify the executed code.
    source = {}
    for folder in ("backend", "scripts"):
        for path in sorted((ROOT / folder).rglob("*.py")):
            source[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    for path in sorted((ROOT / "evaluation").glob("*.json")):
        source[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"revision": revision, "dirty": dirty, "source_hash": digest(source),
            "python": platform.python_version(), "platform": platform.platform(),
            "dependencies": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()},
            "simulator": "pybullet", "orchestration": "deterministic"}


def run_experiment(request: ExperimentRequest, ledger: Ledger, output: Path):
    """Run in a caller-owned output directory; persist errors before re-raising."""
    output.mkdir(parents=True, exist_ok=False)
    run_id = uuid.uuid4().hex
    ledger.create(run_id, request.model_dump())
    telemetry = TelemetryService()
    start = time.perf_counter()
    stage = "planning"
    try:
        ledger.event(run_id, stage, {"role": "experiment_planner", "request": request.model_dump()})
        scenarios = generate_scenarios(request.scenario_count, request.seed)
        manifest = [s.model_dump(mode="json") for s in scenarios]
        (output / "scenarios.json").write_text(json.dumps(manifest, indent=2) + "\n")
        scenario_hash = digest(manifest)
        stage = "simulation"
        ledger.event(run_id, stage, {"role": "simulation_operator", "scenario_hash": scenario_hash,
                                     "count": len(scenarios)})
        sim_start = time.perf_counter()
        summary = run_benchmark(scenarios, MissionService(), telemetry, run_id, request.name)
        sim_elapsed = time.perf_counter() - sim_start
        # Exclude transient identity; results retain deterministic scenario IDs and failures.
        semantic = summary.model_dump(mode="json", exclude={"benchmark_id", "benchmark_name"})
        infrastructure_failure = any("Execution failed:" in (r.message or "") for r in summary.scenario_results)
        stage = "evaluation"
        passed = not infrastructure_failure and summary.success_rate >= request.minimum_success_rate
        ledger.event(run_id, stage, {"role": "evaluator", "passed": passed,
                                    "minimum_success_rate": request.minimum_success_rate,
                                    "simulation_seconds": sim_elapsed})
        report = ExperimentReport(
            run_id=run_id, status="failed" if infrastructure_failure else "completed", request=request,
            scenario_hash=scenario_hash, outcome_hash=digest(semantic), evaluation_passed=passed,
            summary={**semantic, "simulation_seconds": sim_elapsed,
                     "elapsed_seconds": time.perf_counter()-start,
                     "inference_cost_usd": None, "collision_safety_evaluated": False},
            provenance=provenance(), limitations=LIMITATIONS)
        ledger.event(run_id, "reporting", {"role": "reporter", "outcome_hash": report.outcome_hash})
        ledger.finish(report)
        (output / "report.json").write_text(report.model_dump_json(indent=2) + "\n")
        # Export the existing mission decision traces without depending on an internal store.
        traces = telemetry.export()
        (output / "mission-traces.json").write_text(json.dumps(traces, indent=2) + "\n")
        (output / "workflow.json").write_text(json.dumps(ledger.read(run_id), indent=2) + "\n")
        return report
    except Exception as exc:
        ledger.event(run_id, "failed", {"failed_stage": stage, "error_type": type(exc).__name__,
                                         "message": str(exc)})
        (output / "workflow.json").write_text(json.dumps(ledger.read(run_id), indent=2) + "\n")
        raise


def compare_reports(left: dict, right: dict):
    """Exact semantic repeat check, not a statistical policy-improvement claim."""
    same_scenarios = left["scenario_hash"] == right["scenario_hash"]
    same_source = left["provenance"]["source_hash"] == right["provenance"]["source_hash"]
    return {"same_scenarios": same_scenarios, "same_source": same_source,
            "same_outcomes": left["outcome_hash"] == right["outcome_hash"],
            "reproduced": same_scenarios and same_source and left["outcome_hash"] == right["outcome_hash"]
                          and left["status"] == right["status"] == "completed"}
