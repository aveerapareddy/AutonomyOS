import argparse
import json
from pathlib import Path
from backend.knowledge.semantic import query,MODEL,REVISION
from backend.knowledge.retrieval import EngineeringIndex,evaluate,sha

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--index',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    root=Path(__file__).resolve().parents[1];labels_path=root/'evaluation/retrieval-v1.json';labels=json.loads(labels_path.read_text())
    index=EngineeringIndex(root,root/'knowledge/engineering-v3.json');result={'model_id':MODEL,'revision':REVISION,'device':'cpu','labels_sha256':sha(labels_path.read_bytes()),'splits':{}}
    for split in ['development','held_out']:
        rows=[]
        for case in labels[split]:
            hits=query(root,a.index,case['query'])['sources'];ranks=[i+1 for i,h in enumerate(hits) if h['document_id'] in case['relevant']]
            rows.append({'id':case['id'],'hits':hits,'reciprocal_rank':1/min(ranks) if ranks else 0,'recall_at_3':len(ranks)/len(case['relevant'])})
        result['splits'][split]={'semantic_mrr':sum(r['reciprocal_rank'] for r in rows)/len(rows),'semantic_recall_at_3':sum(r['recall_at_3'] for r in rows)/len(rows),'lexical_reference':evaluate(index,labels[split]),'cases':rows}
    result['limitations']=['Same small hand-authored eight-query smoke dataset; no improvement or generalization claim.','Semantic chunked retrieval and lexical full-file reference have different retrieval units.']
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({s:{k:v for k,v in r.items() if k in ['semantic_mrr','semantic_recall_at_3']} for s,r in result['splits'].items()},indent=2))
