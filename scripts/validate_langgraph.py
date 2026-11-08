"""Saved-model LangGraph demo with explicitly automated validation review."""
import argparse
import json
from pathlib import Path
from backend.experiments.agent_workflow import AgentWorkflow,WorkflowPolicy
from backend.experiments.graph_workflow import run_graph
from backend.experiments.runner import provenance

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--inference',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    human=AgentWorkflow(a.output/'human-policy',WorkflowPolicy(max_scenarios=10))
    pending=human.submit_inference(a.inference);paused=run_graph(human.root,pending['id'],policy=human.policy)
    assert paused['paused'] and human.get(pending['id'])['call_count']==0
    validation=AgentWorkflow(a.output/'validation-policy',WorkflowPolicy(max_scenarios=10,require_human_review=False))
    item=validation.submit_inference(a.inference)
    first=run_graph(validation.root,item['id'],policy=validation.policy);assert first['paused']
    validation.approve(item['id'],item['digest'],'automated-validation-runner','automated_validation')
    completed=run_graph(validation.root,item['id'],resume=True,policy=validation.policy)
    repeated=run_graph(validation.root,item['id'],resume=True,policy=validation.policy)
    state=validation.get(item['id'])
    result={'passed':completed['evaluation_passed'] and repeated['evaluation_passed'] and state['call_count']==1,
            'source':provenance(),'human_approval_claimed':False,'review_kind':'automated_validation',
            'default_human_policy_paused':paused,'validation_graph':completed,'tool_calls':state['call_count'],
            'workflow':state,'limitations':['Imported preserved live GPU inference; no new model call in this CPU demo.','Validation policy explicitly permits automated review; the default human-review proposal remains pending.']}
    (a.output/'summary.json').write_text(json.dumps(result,indent=2)+'\n');human.export(pending['id']);validation.export(item['id'])
    print(json.dumps({key:result[key] for key in ['passed','human_approval_claimed','review_kind','tool_calls']},indent=2));raise SystemExit(0 if result['passed'] else 1)
