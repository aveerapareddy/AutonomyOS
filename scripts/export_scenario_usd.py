"""Export a real seeded scenario with the optional usd-core dependency."""
import argparse
from pathlib import Path
from backend.integrations.openusd import export_scenario
from backend.scenarios.generator import generate_scenarios

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    export_scenario(generate_scenarios(1, args.seed)[0], args.output)
    print(args.output)
