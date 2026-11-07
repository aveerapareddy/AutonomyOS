from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import pytest
from pydantic import ValidationError

from backend.experiments.agent_workflow import AgentWorkflow, WorkflowError, WorkflowPolicy, ToolProposal, ModelSource
from backend.experiments.models import ExperimentRequest


def proposal(count=1, **args):
    return ToolProposal(arguments=ExperimentRequest(scenario_count=count, seed=42, **args),
                        source=ModelSource(model_id='test-fixture',revision='a'*40,artifact_sha256='b'*64,
                                           input_tokens=10,output_tokens=20))


def approve(workflow, item):
    workflow.approve(item['id'], item['digest'], 'test-operator')


def test_unapproved_proposal_never_invokes_tool(tmp_path, monkeypatch):
    workflow = AgentWorkflow(tmp_path)
    item = workflow.submit(proposal())
    monkeypatch.setattr(workflow, '_invoke', lambda *a: pytest.fail('Tool must not execute'))
    with pytest.raises(WorkflowError, match='approval'):
        workflow.execute(item['id'])
    assert workflow.get(item['id'])['call_count'] == 0


def test_approval_is_bound_to_exact_proposal_and_policy(tmp_path):
    workflow = AgentWorkflow(tmp_path)
    item = workflow.submit(proposal())
    with pytest.raises(WorkflowError, match='does not match'):
        workflow.approve(item['id'], 'wrong', 'operator')
    assert workflow.get(item['id'])['status'] == 'awaiting_approval'
    with pytest.raises(WorkflowError, match='Policy changed'):
        AgentWorkflow(tmp_path, WorkflowPolicy(max_scenarios=50)).approve(item['id'],item['digest'],'operator')


def test_approval_survives_restart_and_execution_is_cached(tmp_path):
    workflow = AgentWorkflow(tmp_path)
    item = workflow.submit(proposal())
    approve(workflow, item)
    restarted = AgentWorkflow(tmp_path)
    result = restarted.execute(item['id'])
    assert result['experiment']['evaluation_passed']
    assert restarted.execute(item['id']) == result
    state = restarted.get(item['id'])
    assert state['call_count'] == 1
    assert state['status'] == 'completed'
    assert [e['event'] for e in state['events']] == ['proposal_submitted','proposal_approved','tool_started','tool_completed']
    assert (tmp_path/item['id']/'workflow.json').exists()


def test_default_policy_requires_human_review(tmp_path):
    workflow = AgentWorkflow(tmp_path)
    item = workflow.submit(proposal())
    with pytest.raises(WorkflowError, match='Human review'):
        workflow.approve(item['id'],item['digest'],'test-runner',review_kind='automated_validation')


def test_token_and_scenario_budgets(tmp_path):
    with pytest.raises(WorkflowError, match='Scenario budget'):
        AgentWorkflow(tmp_path/'count',WorkflowPolicy(max_scenarios=1)).submit(proposal(2))
    with pytest.raises(WorkflowError, match='token budget'):
        AgentWorkflow(tmp_path/'tokens',WorkflowPolicy(max_model_tokens=29)).submit(proposal())


def test_tool_call_budget_is_checked_before_execution(tmp_path, monkeypatch):
    workflow = AgentWorkflow(tmp_path,WorkflowPolicy(max_tool_calls=0))
    item = workflow.submit(proposal()); approve(workflow,item)
    monkeypatch.setattr(workflow,'_invoke',lambda *a:pytest.fail('Budget bypass'))
    with pytest.raises(WorkflowError,match='budget exhausted'):
        workflow.execute(item['id'])
    assert workflow.get(item['id'])['call_count'] == 0


def test_expired_approvals_do_not_execute(tmp_path):
    workflow = AgentWorkflow(tmp_path); item=workflow.submit(proposal()); approve(workflow,item)
    with workflow.connect() as db: db.execute('UPDATE proposals SET expires_at=0 WHERE id=?',(item['id'],))
    with pytest.raises(WorkflowError,match='expired'): workflow.execute(item['id'])


def test_rejected_proposal_cannot_be_approved_or_executed(tmp_path):
    workflow=AgentWorkflow(tmp_path); item=workflow.submit(proposal())
    workflow.reject(item['id'],'reviewer','insufficient experiment specification')
    with pytest.raises(WorkflowError): approve(workflow,item)
    with pytest.raises(WorkflowError): workflow.execute(item['id'])
    assert workflow.get(item['id'])['status']=='rejected'


def test_mutated_approved_body_is_rejected(tmp_path):
    workflow=AgentWorkflow(tmp_path); item=workflow.submit(proposal()); approve(workflow,item)
    changed=proposal(2).model_dump_json()
    with workflow.connect() as db: db.execute('UPDATE proposals SET body=? WHERE id=?',(changed,item['id']))
    with pytest.raises(WorkflowError,match='changed after submission'): workflow.execute(item['id'])


def test_allowlist_blocks_arbitrary_tools_and_extra_fields():
    value=proposal().model_dump()
    with pytest.raises(ValidationError): ToolProposal.model_validate({**value,'tool':'shell'})
    with pytest.raises(ValidationError): ToolProposal.model_validate({**value,'approval':'approved'})
    with pytest.raises(ValidationError): ToolProposal.model_validate({**value,'output_path':'/tmp/escape'})


def test_inference_import_revalidates_raw_model_output(tmp_path):
    arguments=ExperimentRequest(scenario_count=1,seed=42).model_dump()
    artifact={'validated':True,'proposal':arguments,'raw_output':json.dumps(arguments),
              'model_id':'fixture','revision':'a'*40,'input_tokens':1,'output_tokens':20}
    path=tmp_path/'inference.json'; path.write_text(json.dumps(artifact))
    workflow=AgentWorkflow(tmp_path/'workflow'); state=workflow.submit_inference(path)
    assert state['body']['source']['accounting_trust']=='imported_local_report'
    assert (workflow.root/state['id']/'inference.json').read_bytes()==path.read_bytes()
    artifact['raw_output']='{"tool":"shell","arguments":{"command":"delete"}}'
    path.write_text(json.dumps(artifact))
    with pytest.raises(ValidationError): workflow.submit_inference(path)


def test_failed_tool_is_durable_and_not_automatically_retried(tmp_path,monkeypatch):
    workflow=AgentWorkflow(tmp_path); item=workflow.submit(proposal()); approve(workflow,item)
    monkeypatch.setattr(workflow,'_invoke',lambda *a:7)
    with pytest.raises(WorkflowError,match='exit code 7'): workflow.execute(item['id'])
    state=AgentWorkflow(tmp_path).get(item['id'])
    assert state['status']=='failed' and state['call_count']==1
    assert state['events'][-1]['event']=='tool_failed'
    with pytest.raises(WorkflowError,match='not automatically retried'): workflow.execute(item['id'])


def test_process_timeout_really_terminates_child(tmp_path):
    with pytest.raises(WorkflowError,match='timed out'):
        AgentWorkflow._invoke([sys.executable,'-c','import time; time.sleep(30)'],tmp_path/'timeout.log',.1)


def test_concurrent_execute_does_not_dispatch_twice(tmp_path,monkeypatch):
    workflow=AgentWorkflow(tmp_path); item=workflow.submit(proposal()); approve(workflow,item)
    entered=threading.Event(); release=threading.Event(); calls=[]
    def blocking(*args):
        calls.append(1); entered.set(); release.wait(5); return 1
    monkeypatch.setattr(workflow,'_invoke',blocking)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first=pool.submit(workflow.execute,item['id']); assert entered.wait(5)
        with pytest.raises(WorkflowError,match='not automatically retried'): workflow.execute(item['id'])
        release.set()
        with pytest.raises(WorkflowError): first.result()
    assert len(calls)==1


def test_model_name_cannot_select_a_path_or_shell_command(tmp_path):
    with tempfile.TemporaryDirectory(prefix='aos-proof-',dir='/tmp') as scratch:
        marker=Path(scratch)/'marker'
        workflow=AgentWorkflow(tmp_path/'work')
        item=workflow.submit(proposal(name='../../escape;$(touch '+str(marker)+')'))
        approve(workflow,item); result=workflow.execute(item['id'])
        assert result['experiment']['request']['name'].startswith('../../escape')
        assert not marker.exists()
        assert (workflow.root/item['id']/'run/report.json').exists()


def test_denied_approval_attempt_is_durably_audited(tmp_path):
    workflow=AgentWorkflow(tmp_path); item=workflow.submit(proposal())
    with pytest.raises(WorkflowError): workflow.approve(item['id'],'bad-digest','reviewer')
    events=AgentWorkflow(tmp_path).get(item['id'])['events']
    assert events[-1]['event']=='approval_denied'
    assert events[-1]['payload']['tool_dispatched'] is False


def test_tool_cannot_substitute_a_different_experiment_report(tmp_path,monkeypatch):
    from backend.experiments.models import ExperimentReport
    workflow=AgentWorkflow(tmp_path); item=workflow.submit(proposal()); approve(workflow,item)
    def substituted(*args):
        folder=tmp_path/item['id']/'run'; folder.mkdir()
        wrong=ExperimentReport(run_id='wrong',status='completed',request=ExperimentRequest(seed=999),
                               scenario_hash='x',outcome_hash='y',evaluation_passed=True,summary={},
                               provenance={},limitations=[])
        (folder/'report.json').write_text(wrong.model_dump_json())
        return 0
    monkeypatch.setattr(workflow,'_invoke',substituted)
    with pytest.raises(WorkflowError,match='independent request'):
        workflow.execute(item['id'])
    assert workflow.get(item['id'])['status']=='failed'


def test_input_artifact_write_failure_cannot_leave_an_executable_proposal(tmp_path,monkeypatch):
    arguments=ExperimentRequest(scenario_count=1,seed=42).model_dump()
    artifact={'validated':True,'proposal':arguments,'raw_output':json.dumps(arguments),
              'model_id':'fixture','revision':'a'*40,'input_tokens':1,'output_tokens':20}
    path=tmp_path/'input.json';path.write_text(json.dumps(artifact))
    workflow=AgentWorkflow(tmp_path/'workflow')
    original=Path.write_bytes
    def full_disk(target,raw):
        if target.name=='inference.json' and workflow.root in target.parents:
            raise OSError('simulated full disk')
        return original(target,raw)
    monkeypatch.setattr(Path,'write_bytes',full_disk)
    with pytest.raises(OSError,match='full disk'): workflow.submit_inference(path)
    with workflow.connect() as db: row=db.execute('SELECT id FROM proposals').fetchone()
    state=workflow.get(row['id'])
    assert state['status']=='failed' and state['call_count']==0
    with pytest.raises(WorkflowError): workflow.approve(state['id'],state['digest'],'operator')
