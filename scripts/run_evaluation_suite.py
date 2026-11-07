"""Real simulator contract cases, including expected navigation failures."""
import argparse
import json
from pathlib import Path
from backend.scenarios.scenario_config import ScenarioConfig
from backend.scenarios.benchmark_runner import run_benchmark
from backend.services.mission_service import MissionService
from backend.services.telemetry_service import TelemetryService
from backend.experiments.runner import digest, provenance


def evaluate(suite_path: Path):
    suite = json.loads(suite_path.read_text())
    scenarios = [ScenarioConfig(
        scenario_id=c["id"], world_bounds=(-3, 3, -3, 3),
        robot_start_position=c["start"], target_position=c["target"],
        obstacle_positions=c["obstacles"], obstacle_types=["block"] * len(c["obstacles"]))
        for c in suite["cases"]]
    summary = run_benchmark(scenarios, MissionService(), TelemetryService(), "reference", "reference")
    cases = [{"id": c["id"], "expected_success": c["expected_success"], "actual_success": r.success,
              "matched": c["expected_success"] == r.success, "result": r.model_dump(mode="json")}
             for c, r in zip(suite["cases"], summary.scenario_results)]
    # Expected failure only counts when navigation rejected the path, never a runtime outage.
    passed = all(c["matched"] and (c["actual_success"] or c["result"]["message"] == "No path found") for c in cases)
    return {"suite_hash": digest(suite), "description": suite["description"],
            "passed": passed, "matched_cases": sum(c["matched"] for c in cases),
            "total_cases": len(cases), "cases": cases, "provenance": provenance()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", type=Path, default=Path("evaluation/reference.json"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/evaluation.json"))
    args = parser.parse_args()
    report = evaluate(args.suite)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(f'{report["matched_cases"]}/{report["total_cases"]} contract outcomes matched; passed={report["passed"]}')
    raise SystemExit(0 if report["passed"] else 1)
