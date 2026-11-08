import pytest
from backend.experiments.agent_workflow import AgentWorkflow,WorkflowPolicy,WorkflowError
from backend.experiments.graph_workflow import run_graph
from backend.tests.test_agent_workflow import proposal


def test_langgraph_checkpoint_restart_and_exactly_one_tool_dispatch(tmp_path):
    policy=WorkflowPolicy(max_scenarios=10);controller=AgentWorkflow(tmp_path,policy)
    item=controller.submit(proposal())
    first=run_graph(tmp_path,item['id'])
    assert first['paused'] and first['next_nodes']==['review_gate']
    assert controller.get(item['id'])['call_count']==0
    # Test reviewer fixture, not a claimed real-person review.
    controller.approve(item['id'],item['digest'],'test-reviewer')
    restored=run_graph(tmp_path,item['id'],resume=True)
    assert not restored['paused'] and restored['evaluation_passed']
    assert controller.get(item['id'])['call_count']==1
    assert run_graph(tmp_path,item['id'],resume=True)['evaluation_passed']
    assert controller.get(item['id'])['call_count']==1
    assert (tmp_path/'graph-checkpoints.sqlite3').exists()


def test_langgraph_resume_without_review_cannot_execute(tmp_path):
    controller=AgentWorkflow(tmp_path,WorkflowPolicy(max_scenarios=10));item=controller.submit(proposal())
    assert run_graph(tmp_path,item['id'])['paused']
    with pytest.raises(WorkflowError,match='resume cannot replace'):run_graph(tmp_path,item['id'],resume=True)
    assert controller.get(item['id'])['call_count']==0
