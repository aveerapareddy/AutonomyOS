"""Live model planning contracts, with exact argument checks and failure evidence."""
import argparse
import json
from pathlib import Path
from backend.integrations.huggingface import propose, validate_proposal
from backend.experiments.runner import digest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--revision", required=True)
    parser.add_argument("--model", default="nvidia/Llama-3.1-Nemotron-Nano-8B-v1")
    parser.add_argument("--suite", type=Path, default=Path("evaluation/agent_prompts.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    suite = json.loads(args.suite.read_text())
    results = []
    for case in suite["cases"]:
        result = {"id": case["id"], "expected": case["expected"], "matched": False}
        try:
            raw, metadata = propose(case["objective"], args.model, args.revision)
            result["inference"] = metadata
            proposal = validate_proposal(raw).model_dump()
            result["proposal"] = proposal
            result["matched"] = all(proposal[k] == v for k, v in case["expected"].items())
        except Exception as exc:
            result["error_type"] = type(exc).__name__
            result["error"] = str(exc)
        results.append(result)
        # Preserve partial evidence if a later case or process fails.
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({"suite_hash": digest(suite), "scope": suite["scope"],
            "completed_cases": len(results), "total_cases": len(suite["cases"]),
            "passed": len(results) == len(suite["cases"]) and all(r["matched"] for r in results),
            "results": results}, indent=2) + "\n")
    print(f'{sum(r["matched"] for r in results)}/{len(results)} exact planning contracts matched')
    return 0 if all(r["matched"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
