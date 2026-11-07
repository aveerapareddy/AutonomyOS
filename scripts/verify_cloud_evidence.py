import argparse
import json
from pathlib import Path
from backend.experiments.evidence import verify_archive

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Verify cloud logs/results before permitting shutdown')
    parser.add_argument('archive', type=Path)
    parser.add_argument('--extract-to', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify_archive(args.archive, args.extract_to), indent=2))
