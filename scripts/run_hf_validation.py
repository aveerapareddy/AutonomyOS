"""Produce a real inference evidence file; does not automatically execute proposals."""
import argparse
import json
from pathlib import Path
from backend.integrations.huggingface import propose, validate_proposal
from backend.integrations.nim import proposal_hash


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="nvidia/Llama-3.1-Nemotron-Nano-8B-v1")
    parser.add_argument("--revision", required=True, help="Full reviewed Hugging Face commit SHA")
    parser.add_argument("--objective", default="Propose 5 warehouse scenarios using seed 42 and a minimum success rate of 0.8.")
    parser.add_argument("--output", type=Path, default=Path("artifacts/hf-inference.json"))
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Choose a new output path to preserve existing evidence")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    raw, metadata = propose(args.objective, args.model, args.revision)
    metadata["objective"] = args.objective
    try:
        proposal = validate_proposal(raw)
        metadata.update(validated=True, proposal=proposal.model_dump(), proposal_hash=proposal_hash(proposal))
    except ValueError as exc:
        metadata.update(validated=False, validation_error=str(exc))
    args.output.write_text(json.dumps(metadata, indent=2) + "\n")
    print(f'Proposal validated={metadata["validated"]}; evidence={args.output}')
    return 0 if metadata["validated"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
