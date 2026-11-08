import json
import pytest
from fastapi.testclient import TestClient
from backend.api.main import app
from backend.api.routes.workflows import operator
from backend.core.config import get_settings
from backend.experiments.agent_workflow import AgentWorkflow,WorkflowPolicy
from backend.tests.test_agent_workflow import proposal

TOKEN='test-operator-token-with-24-characters'

@pytest.fixture
def api(tmp_path,monkeypatch):
    monkeypatch.setenv('AUTONOMY_WORKFLOW_DIRECTORY',str(tmp_path))
    monkeypatch.setenv('AUTONOMY_OPERATOR_TOKEN',TOKEN)
    monkeypatch.setenv('AUTONOMY_PUBLIC_DEMO','false')
    get_settings.cache_clear()
    yield TestClient(app),AgentWorkflow(tmp_path,WorkflowPolicy(max_scenarios=10))
    get_settings.cache_clear()


def test_authentication_is_required_and_public_mode_blocks(api,monkeypatch):
    client,workflow=api
    assert client.get('/workflows').status_code==401
    assert client.get('/workflows',headers={'Authorization':'Bearer wrong'}).status_code==401
    assert client.get('/workflows',headers={'Authorization':'Bearer '+TOKEN}).status_code==200
    monkeypatch.setenv('AUTONOMY_PUBLIC_DEMO','true');get_settings.cache_clear()
    assert client.get('/workflows',headers={'Authorization':'Bearer '+TOKEN}).status_code==403


def test_review_execution_and_cached_result_through_api(api):
    client,workflow=api
    item=workflow.submit(proposal())
    headers={'Authorization':'Bearer '+TOKEN}
    path='/workflows/'+item['id']
    assert client.post(path+'/execute',headers=headers).status_code==422
    assert client.post(path+'/approve',headers=headers,json={'digest':'a'*64,'actor':'test reviewer'}).status_code==422
    assert client.post(path+'/approve',headers=headers,json={'digest':item['digest'],'actor':'test reviewer'}).status_code==200
    result=client.post(path+'/execute',headers=headers)
    assert result.status_code==200
    assert result.json()['status']=='completed'
    assert result.json()['report']['experiment']['evaluation_passed']
    assert client.post(path+'/execute',headers=headers).json()['call_count']==1
    assert client.get('/workflows',headers=headers).json()[0]['id']==item['id']


def test_import_revalidation_size_limit_and_rejection(api):
    client,workflow=api;headers={'Authorization':'Bearer '+TOKEN}
    assert client.post('/workflows/import',content=b'x'*256001,headers=headers).status_code==413
    assert client.post('/workflows/import',json={'validated':True},headers=headers).status_code==422
    report={'model_id':'test-fixture','revision':'a'*40,'input_tokens':10,'output_tokens':20,
            'proposal':proposal().arguments.model_dump(),'validated':True,
            'raw_output':proposal().arguments.model_dump_json()}
    response=client.post('/workflows/import',json=report,headers=headers)
    assert response.status_code==201
    ident=response.json()['id'];path='/workflows/'+ident
    assert (workflow.root/ident/'inference.json').exists()
    assert client.post(path+'/reject',json={'actor':'test reviewer','reason':'test rejection'},headers=headers).json()['status']=='rejected'
    assert client.post(path+'/execute',headers=headers).status_code==422


def test_overlapping_api_simulator_calls_are_rejected(api):
    from backend.api.simulation_gate import simulation_slot
    client,_=api
    mission=client.post('/missions',json={'mission_text':'Go to target'}).json()['mission_id']
    with simulation_slot():
        assert client.post('/missions/'+mission+'/execute').status_code==409


def test_scene_metadata_available_while_real_simulation_is_in_progress(api,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from backend.simulator.environment import SimulationEnvironment
    client,_=api
    monkeypatch.setenv('AUTONOMY_PLANNER_MODE','rule_based')
    entered=Event();release=Event();original=SimulationEnvironment.step
    def paused_step(self,action):
        if not entered.is_set():
            entered.set()
            assert release.wait(5)
        return original(self,action)
    monkeypatch.setattr(SimulationEnvironment,'step',paused_step)
    ident=client.post('/missions',json={'mission_text':'Go to target'}).json()['mission_id']
    with ThreadPoolExecutor() as pool:
        future=pool.submit(client.post,'/missions/'+ident+'/execute')
        try:
            assert entered.wait(5)
            response=client.get('/missions/'+ident+'/telemetry').json()
            assert not future.done()
            ready=next(e for e in response['events'] if e['event_type']=='scene_ready')
            assert ready['payload']['world_bounds'] and ready['payload']['waypoints']
            cursor=response['events'][-1]['sequence']
        finally:
            release.set()
        assert future.result().json()['status']=='completed'
    incremental=client.get('/missions/'+ident+'/telemetry',params={'after_sequence':cursor}).json()['events']
    assert all(e['sequence']>cursor for e in incremental)
    assert any(e['event_type']=='robot_state' for e in incremental)
    final=next(e for e in incremental if e['event_type']=='execution_completed')
    assert final['payload']['simulation_time_seconds']>0
