"""Return extractive engineering context with file/line/hash citations."""
import argparse
import json
from pathlib import Path
from backend.knowledge.retrieval import EngineeringIndex

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('question')
    parser.add_argument('--k',type=int,default=3)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    index=EngineeringIndex(root,root/'knowledge/engineering-v4.json')
    print(json.dumps({'corpus_hash':index.corpus_hash,'question':args.question,
                      'answer_mode':'extractive context; no generated answer',
                      'sources':index.search(args.question,args.k)},indent=2))
