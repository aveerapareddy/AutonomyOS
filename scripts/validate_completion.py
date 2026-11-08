"""Collect actual local completion evidence in a fresh output directory."""
import argparse
import json
from pathlib import Path
from backend.operations.jobs import JobStore,JobRequest
from backend.operations.site import SiteSpec
from backend.experiments.models import ExperimentRequest
from backend.knowledge.graph import build_graph
from backend.knowledge.answers import answer
from backend.experiments.runner import provenance
from backend.integrations.openusd import export_scenario


def run(output):
    output.mkdir(parents=True,exist_ok=False)
    root=Path(__file__).resolve().parents[1];store=JobStore(output/'jobs')
    experiment=store.submit(JobRequest(experiment=ExperimentRequest(scenario_count=10,seed=42)),'completion-experiment')
    site=SiteSpec.model_validate_json((root/'evaluation/site-v1.json').read_text())
    imported=store.submit(JobRequest(kind='site',site=site),'completion-site')
    while store.run_one():pass
    e,s=store.get(experiment['id']),store.get(imported['id'])
    assert e['status']=='completed' and s['status']=='completed'
    assert e['result']['report']['evaluation_passed']
    assert s['result']['summary']['status']=='completed'
    assert store.submit(JobRequest(kind='site',site=site),'completion-site')['id']==imported['id']
    graph=build_graph(store);(output/'graph.json').write_text(json.dumps(graph,indent=2)+'\n')
    questions=['How are concurrent SQLite event sequence numbers allocated?',
               'What checks validate an evidence archive?',
               'How does cancellation stop an isolated job?',
               'zzzzqwertyuiop']
    answers=[answer(root,q) for q in questions]
    (output/'answers.json').write_text(json.dumps(answers,indent=2)+'\n')
    assert answers[-1]['abstained'] and any(a['sources'] for a in answers[:-1])
    export_scenario(site.scenario(),output/'site.usda')
    from pxr import Usd,UsdGeom
    stage=Usd.Stage.Open(str(output/'site.usda'));scale=UsdGeom.Xformable(stage.GetPrimAtPath('/World/obstacle_0')).GetOrderedXformOps()[1].Get()
    assert list(scale)==[.8,8.,3.] or all(abs(a-b)<1e-5 for a,b in zip(scale,[.8,8,3]))
    result={'passed':True,'source':provenance(),'experiment':{'successes':e['result']['report']['summary']['success_count'],'total':10},
            'site':{'status':s['result']['summary']['status'],'simulator_steps':s['result']['summary']['simulator_steps'],'events':len(s['result']['telemetry'])},
            'graph':{'nodes':len(graph['nodes']),'edges':len(graph['edges'])},
            'idempotency_passed':True,'grounded_answer_count':sum(not a['abstained'] for a in answers),
            'unknown_query_abstained':True,'site_usd_dimensions_verified':True}
    (output/'summary.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    print(json.dumps(run(a.output),indent=2))
