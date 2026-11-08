import argparse
import json
from pathlib import Path
from backend.experiments.graph_workflow import run_graph

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--id',required=True);p.add_argument('--resume',action='store_true');a=p.parse_args()
    print(json.dumps(run_graph(a.root,a.id,a.resume),indent=2))
