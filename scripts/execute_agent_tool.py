"""One fixed experiment tool, invoked without a shell by the governed workflow."""
import argparse
from pathlib import Path
from backend.experiments.models import ExperimentRequest
from backend.experiments.ledger import Ledger
from backend.experiments.runner import run_experiment

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--ledger', type=Path, required=True)
    args = parser.parse_args()
    request = ExperimentRequest.model_validate_json(args.request.read_text())
    report = run_experiment(request, Ledger(args.ledger), args.output)
    raise SystemExit(0 if report.status == 'completed' and report.evaluation_passed else 1)
