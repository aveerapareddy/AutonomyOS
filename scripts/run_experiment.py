"""Run from repository root: python -m scripts.run_experiment --help."""
import argparse
import json
from pathlib import Path

from backend.experiments.ledger import Ledger
from backend.experiments.models import ExperimentRequest
from backend.experiments.runner import compare_reports, run_experiment


def main():
    parser = argparse.ArgumentParser(description="Run a real, seeded PyBullet experiment")
    parser.add_argument("--output", type=Path, default=Path("artifacts/run"))
    parser.add_argument("--ledger", type=Path, default=Path("artifacts/experiments.sqlite"))
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--minimum-success-rate", type=float, default=0.8)
    parser.add_argument("--compare", type=Path, help="Prior report.json; require exact semantic reproduction")
    args = parser.parse_args()
    request = ExperimentRequest(seed=args.seed, scenario_count=args.count,
                                minimum_success_rate=args.minimum_success_rate)
    report = run_experiment(request, Ledger(args.ledger), args.output)
    print(report.model_dump_json(indent=2))
    reproduced = True
    if args.compare:
        comparison = compare_reports(json.loads(args.compare.read_text()), report.model_dump(mode="json"))
        (args.output / "comparison.json").write_text(json.dumps(comparison, indent=2) + "\n")
        print(json.dumps(comparison))
        reproduced = comparison["reproduced"]
    return 0 if report.evaluation_passed and reproduced else 1


if __name__ == "__main__":
    raise SystemExit(main())
