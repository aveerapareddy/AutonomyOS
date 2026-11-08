import argparse
import json
from pathlib import Path
from backend.knowledge.retrieval import EngineeringIndex, evaluate, sha

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    index=EngineeringIndex(root,root/'knowledge/engineering-v1.json')
    labels_path=root/'evaluation/retrieval-v1.json'
    labels=json.loads(labels_path.read_text())
    report={'method':'BM25 lexical retrieval; extractive citations, no generated answer',
            'labels_sha256':sha(labels_path.read_bytes()),'label_origin':labels['label_origin'],
            'development':evaluate(index,labels['development']),
            'held_out':evaluate(index,labels['held_out']),
            'limitations':['Eight first-party source documents and eight hand-authored questions.',
                           'Fixed BM25 parameters; no tuning on the held-out queries.',
                           'No embedding/vector model, LLM answer generation or external knowledge.']}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as f: json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps({s:{key:report[s][key] for key in ('case_count','mean_recall_at_k','mean_reciprocal_rank')} for s in ('development','held_out')},indent=2))
