"""Freeze selected first-party source excerpts. Review labels separately before evaluation."""
import json
from pathlib import Path
from backend.knowledge.retrieval import sha

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
 ('queue','Isolated subprocess jobs atomic claim idempotency cancellation and heartbeat','backend/operations/jobs.py'),
 ('site','Validated metric site geometry and occupancy import','backend/operations/site.py'),
 ('camera','Camera image projection field of view in degrees','backend/simulator/camera.py'),
 ('execution','Waypoint execution tolerance turning budget and simulator steps','backend/simulator/execution_engine.py'),
 ('workflow','Agent workflow approval policy digest timeout and tool dispatch','backend/experiments/agent_workflow.py'),
 ('evidence','Evidence archive integrity checks shutdown validation gates','backend/experiments/evidence.py'),
 ('journal','Durable SQLite mission events transactional sequence allocation','backend/storage/sqlite_journal.py'),
 ('scenario','Seeded scenario generation obstacle target and robot start','backend/scenarios/generator.py'),
 ('physics','Kinematic robot actions forward turning physics collision limitations','backend/simulator/robot.py'),
 ('usd','OpenUSD geometry export meters Z axis and stage validation','backend/integrations/openusd.py'),
 ('inference','Hugging Face PyTorch Nemotron model revision token usage','backend/integrations/huggingface.py'),
]

def build():
    docs=[]
    for ident,title,relative in SOURCES:
        raw=(ROOT/relative).read_bytes();lines=raw.decode().splitlines()
        docs.append({'id':ident,'title':title,'path':relative,'source_sha256':sha(raw),
                     'start_line':1,'end_line':len(lines),'excerpt':'\n'.join(lines)})
    return {'schema_version':1,'version':'engineering-v4','documents':docs}

if __name__ == '__main__':
    (ROOT/'knowledge/engineering-v4.json').write_text(json.dumps(build(),indent=2)+'\n')
