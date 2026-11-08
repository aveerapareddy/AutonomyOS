"""Evaluate extractive citation integrity and declared unsupported-query contracts."""
import argparse
import json
from pathlib import Path
from backend.knowledge.answers import answer
from backend.knowledge.retrieval import sha

CASES=[('sqlite','How are concurrent SQLite event sequence numbers allocated?',False),
 ('archive','What checks validate an evidence archive?',False),
 ('waypoint','Where is the waypoint tolerance configured?',False),
 ('camera','How is the camera field of view configured?',False),
 ('unknown','zzzzqwertyuiop',True),('medical','Diagnose cholera',True),
 ('financial','Forecast bitcoin valuation',True),('unrelated','Martian botanical taxonomy',True)]

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();root=Path(__file__).resolve().parents[1];rows=[]
    for ident,question,expected_abstain in CASES:
        result=answer(root,question);valid=True
        for source in result['sources']:
            c=source['citation'];path=root/c['path'];lines=path.read_text().splitlines()
            valid &= source['quote']==lines[c['start_line']-1].strip() and sha(path.read_bytes())==c['source_sha256']
        rows.append({'id':ident,'expected_abstention':expected_abstain,'abstention_contract_passed':result['abstained']==expected_abstain,'citations_exact':bool(valid),'result':result})
    report={'passed':all(r['abstention_contract_passed'] and r['citations_exact'] for r in rows),'cases':rows,
      'limitations':['Hand-authored small smoke set.','Exact citations are not an independent measure of answer completeness or reasoning accuracy.','Extractive mode has no generated prose or tool execution authority.']}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps({'passed':report['passed'],'case_count':len(rows),'abstention_contracts':[r['abstention_contract_passed'] for r in rows]}));raise SystemExit(0 if report['passed'] else 1)
