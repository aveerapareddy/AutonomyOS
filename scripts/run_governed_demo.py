"""Validate model-to-tool execution with explicitly labeled automated review.

The default workflow requires human review. This diagnostic uses a separate
validation policy and does not claim a human approved the demo proposal.
"""
import argparse
import json
from pathlib import Path
from backend.experiments.agent_workflow import AgentWorkflow, WorkflowError, WorkflowPolicy


def run_demo(inference: Path, output: Path):
    output.mkdir(parents=True, exist_ok=False)
    negative = {}
    default = AgentWorkflow(output / 'default-human-policy')
    pending = default.submit_inference(inference)
    try:
        default.approve(pending['id'],pending['digest'],'validation-runner','automated_validation')
    except WorkflowError:
        negative['default_human_policy_blocks_automated_review'] = True
    else:
        raise AssertionError('Default review gate was bypassed')
    default.export(pending['id'])
    policy = WorkflowPolicy(max_scenarios=10,max_model_tokens=1024,tool_timeout_seconds=15,
                            require_human_review=False)
    workflow = AgentWorkflow(output / 'validation-policy', policy)
    proposal = workflow.submit_inference(inference)
    try:
        workflow.execute(proposal['id'])
    except WorkflowError:
        negative['unapproved_execution_blocked'] = True
    else:
        raise AssertionError('Unapproved execution was permitted')
    try:
        workflow.approve(proposal['id'],'wrong-digest','validation-runner','automated_validation')
    except WorkflowError:
        negative['wrong_digest_approval_blocked'] = True
    else:
        raise AssertionError('Mismatched approval was permitted')
    workflow.approve(proposal['id'],proposal['digest'],'automated-validation-runner','automated_validation')
    restored = AgentWorkflow(output / 'validation-policy',policy)
    result = restored.execute(proposal['id'])
    repeated = restored.execute(proposal['id'])
    state = restored.get(proposal['id'])
    cached = repeated == result and state['call_count'] == 1
    assert cached
    summary = {'passed':all(negative.values()) and cached and result['experiment']['evaluation_passed'],
               'workflow_id':proposal['id'], 'source':proposal['body']['source'],
               'review_kind':'automated_validation', 'human_approval_claimed':False,
               'negative_contracts':negative, 'completed_reexecution_used_cached_result':cached,
               'tool_calls':state['call_count'], 'experiment':result['experiment'],
               'limitations':['Local CLI operator identity is trusted; no multi-user authentication.',
                              'Imported token usage is reported metadata, not independently metered billing.',
                              'Deterministic tools around a real model proposal; no autonomous multi-LLM system.']}
    (output / 'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--inference',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    report=run_demo(args.inference,args.output)
    print(json.dumps({k:report[k] for k in ('passed','workflow_id','tool_calls','review_kind')},indent=2))
    raise SystemExit(0 if report['passed'] else 1)
