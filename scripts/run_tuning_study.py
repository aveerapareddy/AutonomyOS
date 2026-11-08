import argparse
import json
from pathlib import Path
from backend.experiments.tuning import run_study

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description='Run the frozen, bounded controller step-budget study')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=run_study(args.output)
    print(json.dumps({k:result[k] for k in ('selected_budget','training','validation','held_out','claim')},indent=2))
