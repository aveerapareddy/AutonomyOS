from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import time
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from backend.api.main import app
from backend.core.config import get_settings
from backend.operations.jobs import JobStore,JobRequest
from backend.operations.site import SiteSpec,Asset,OccupancyImport
from backend.experiments.models import ExperimentRequest
from backend.knowledge.answers import answer
from backend.knowledge.graph import build_graph
from backend.simulator.world_builder import WorldLayoutSpec,build_world_from_config

ROOT=Path(__file__).resolve().parents[2]

def request(count=1):return JobRequest(experiment=ExperimentRequest(scenario_count=count,seed=42))

def test_jobs_idempotency_atomic_claim_and_cancel(tmp_path):
    store=JobStore(tmp_path)
    with ThreadPoolExecutor() as pool:
        ids=list(pool.map(lambda _:JobStore(tmp_path).submit(request(),'same-request')['id'],range(8)))
    assert len(set(ids))==1
    with pytest.raises(ValueError,match='different'):store.submit(request(2),'same-request')
    with ThreadPoolExecutor() as pool:claims=list(pool.map(lambda _:JobStore(tmp_path).claim(),range(8)))
    assert sum(x is not None for x in claims)==1
    store.cancel(ids[0]);store.finish(ids[0],'completed',{})
    assert store.get(ids[0])['status']=='cancelled'


def test_real_isolated_jobs_restart_and_relationships(tmp_path):
    store=JobStore(tmp_path)
    item=store.submit(request(),'one-real-job')
    assert store.run_one()
    restarted=JobStore(tmp_path);result=restarted.get(item['id'])
    assert result['status']=='completed'
    assert result['result']['report']['evaluation_passed']
    assert restarted.submit(request(),'one-real-job')['id']==item['id']
    assert not restarted.run_one()
    graph=build_graph(restarted)
    assert any(e['relation']=='evaluates' for e in graph['edges'])
    assert (tmp_path/item['id']/'worker.log').exists()


def test_stale_worker_is_terminal_and_never_automatically_retried(tmp_path):
    store=JobStore(tmp_path);item=store.submit(request(),'interrupted-job');store.claim()
    with store.connect() as db:db.execute('UPDATE jobs SET updated=0 WHERE id=?',(item['id'],))
    assert store.claim() is None
    assert store.get(item['id'])['status']=='interrupted'


def test_worker_failure_and_cancellation_do_not_become_success(tmp_path,monkeypatch):
    from backend.operations import jobs
    store=JobStore(tmp_path);item=store.submit(request(),'failed-worker')
    monkeypatch.setattr(jobs.subprocess,'Popen',lambda *a,**kw:(_ for _ in ()).throw(OSError('test spawn failure')))
    assert store.run_one()
    assert store.get(item['id'])['status']=='failed'
    cancelled=store.submit(request(),'cancel-before-run');store.cancel(cancelled['id'])
    assert not store.run_one()
    assert store.get(cancelled['id'])['status']=='cancelled'


def test_site_bounds_asset_and_occupancy_validation():
    site=SiteSpec.model_validate_json((ROOT/'evaluation/site-v1.json').read_text())
    assert site.scenario().obstacle_half_extents[0]==(.4,4,1.5)
    with pytest.raises(ValidationError):SiteSpec(bounds=(0,100,0,100))
    with pytest.raises(ValidationError):SiteSpec(assets=[Asset(id='blocked',x=0,y=0)])
    with pytest.raises(ValidationError):SiteSpec(assets=[Asset(id='bad',x=float('nan'),y=1)])
    with pytest.raises(ValueError):OccupancyImport(resolution=1,cells=[[0,1],[0]],start=(.5,.5,0),target=(1.5,1.5)).to_site()
    occupied=OccupancyImport(resolution=1,cells=[[0,0,0,0],[0,0,0,0],[0,0,0,0],[0,0,0,1]],start=(.5,.5,0),target=(2.5,2.5)).to_site()
    assert occupied.assets[0].half_extents==(.5,.5,.5)


def test_imported_site_real_run_geometry_and_telemetry(tmp_path):
    site=SiteSpec.model_validate_json((ROOT/'evaluation/site-v1.json').read_text())
    store=JobStore(tmp_path);item=store.submit(JobRequest(kind='site',site=site),'site-real-run')
    store.run_one();job=store.get(item['id'])
    assert job['status']=='completed',job['error']
    result=job['result'];assert result['summary']['status']=='completed'
    assert result['summary']['obstacles'][0]['half_extents']==[.4,4.,1.5]
    assert any(e['event_type']=='robot_state' for e in result['telemetry'])
    assert any(n['kind']=='asset' for n in build_graph(store)['nodes'])


def test_grounded_answers_quote_exact_cited_lines_and_abstain():
    result=answer(ROOT,'How are concurrent SQLite event sequence numbers allocated?')
    assert not result['abstained']
    for source in result['sources']:
        citation=source['citation'];lines=(ROOT/citation['path']).read_text().splitlines()
        assert source['quote']==lines[citation['start_line']-1].strip()
    assert answer(ROOT,'zzzzqwertyuiop')['abstained']


def test_role_subject_binding_and_read_only_denials(tmp_path,monkeypatch):
    from backend.experiments.agent_workflow import AgentWorkflow,WorkflowPolicy
    from backend.tests.test_agent_workflow import proposal
    read='reader-account-token-with-at-least-24';review='review-account-token-with-at-least-24'
    accounts=[{'name':'viewer','token_sha256':hashlib.sha256(read.encode()).hexdigest(),'roles':['read']},
              {'name':'reviewer-alice','token_sha256':hashlib.sha256(review.encode()).hexdigest(),'roles':['read','review']}]
    monkeypatch.setenv('AUTONOMY_OPERATOR_ACCOUNTS_JSON',json.dumps(accounts))
    monkeypatch.setenv('AUTONOMY_WORKFLOW_DIRECTORY',str(tmp_path/'workflow'))
    monkeypatch.setenv('AUTONOMY_OPERATIONS_DIRECTORY',str(tmp_path/'jobs'))
    monkeypatch.setenv('AUTONOMY_PUBLIC_DEMO','false');get_settings.cache_clear()
    try:
        client=TestClient(app);headers={'Authorization':'Bearer '+read}
        assert client.get('/operations/identity',headers=headers).json()['name']=='viewer'
        assert client.post('/operations/jobs',headers=headers,json={'key':'denied-job','request':request().model_dump(mode='json')}).status_code==403
        workflow=AgentWorkflow(tmp_path/'workflow',WorkflowPolicy(max_scenarios=10));item=workflow.submit(proposal())
        path='/workflows/'+item['id']+'/approve';body={'digest':item['digest'],'actor':'forged-other-user'}
        assert client.post(path,headers=headers,json=body).status_code==403
        approved=client.post(path,headers={'Authorization':'Bearer '+review},json=body).json()
        assert approved['approval']['actor']=='reviewer-alice'
        assert client.post('/workflows/'+item['id']+'/execute',headers={'Authorization':'Bearer '+review}).status_code==403
    finally:get_settings.cache_clear()


def test_http_telemetry_trace_id_and_metrics_auth(tmp_path,monkeypatch):
    from backend.core.observability import JsonSpanExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    provider=TracerProvider();provider.add_span_processor(SimpleSpanProcessor(JsonSpanExporter(tmp_path)))
    with provider.get_tracer('test').start_as_current_span('verified-span') as span:span.set_attribute('test.passed',True)
    provider.force_flush()
    recorded=json.loads((tmp_path/'http-spans.jsonl').read_text())
    assert recorded['name']=='verified-span' and recorded['attributes']['test.passed']
    response=TestClient(app).get('/health')
    assert len(response.headers['X-Trace-ID'])==32
    assert TestClient(app).get('/operations/metrics').status_code in (401,403)


def test_real_running_worker_cancellation_is_persisted(tmp_path):
    import threading
    store=JobStore(tmp_path);item=store.submit(request(20),'cancel-running-job')
    thread=threading.Thread(target=store.run_one);thread.start()
    deadline=time.monotonic()+5
    while store.get(item['id'])['status']=='queued' and time.monotonic()<deadline:time.sleep(.01)
    store.cancel(item['id']);thread.join(10)
    assert not thread.is_alive()
    assert store.get(item['id'])['status']=='cancelled'


def test_two_workers_execute_distinct_jobs_in_isolated_processes(tmp_path):
    store=JobStore(tmp_path)
    ids=[store.submit(request(),'parallel-job-'+str(i))['id'] for i in range(2)]
    with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(lambda _:JobStore(tmp_path).run_one(),range(2)))
    assert all(store.get(ident)['status']=='completed' for ident in ids)
    assert len({store.get(ident)['result']['report']['run_id'] for ident in ids})==2


def test_api_does_not_implicitly_enable_semantic_inference(tmp_path,monkeypatch):
    monkeypatch.setenv('AUTONOMY_OPERATOR_TOKEN','local-test-read-token-with-24-characters')
    monkeypatch.setenv('AUTONOMY_PUBLIC_DEMO','false')
    monkeypatch.setenv('AUTONOMY_SEMANTIC_PYTHON','')
    get_settings.cache_clear()
    try:
        response=TestClient(app).post('/operations/knowledge',headers={'Authorization':'Bearer local-test-read-token-with-24-characters'},json={'question':'How does the controller work?','method':'semantic'})
        assert response.status_code==503
    finally:get_settings.cache_clear()
