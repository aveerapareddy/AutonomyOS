import argparse
import json
from pathlib import Path
from backend.knowledge.semantic import build,query

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--index',type=Path,required=True);p.add_argument('--build',action='store_true');p.add_argument('--question');a=p.parse_args()
    root=Path(__file__).resolve().parents[1]
    if a.build:
        result=build(root,a.index);print(json.dumps({key:result[key] for key in ['model_id','revision','device','corpus_hash','versions']}))
    else:
        if not a.question:p.error('--question is required for search')
        print(json.dumps(query(root,a.index,a.question)))
