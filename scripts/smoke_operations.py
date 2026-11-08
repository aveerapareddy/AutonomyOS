"""Real authenticated HTTP and worker smoke. Token comes only from environment."""
import argparse
import json
import os
from pathlib import Path
import time
import urllib.request
import urllib.error

def run(base,output):
    token=os.environ['AUTONOMY_OPERATOR_TOKEN']
    def request(path,body=None):
        req=urllib.request.Request(base+path,data=json.dumps(body).encode() if body is not None else None,
             headers={'Content-Type':'application/json','Authorization':'Bearer '+token})
        with urllib.request.urlopen(req,timeout=30) as response:return json.load(response),response.headers.get('X-Trace-ID')
    identity,_=request('/operations/identity')
    key='smoke-'+str(time.time_ns())
    payload={'key':key,'request':{'kind':'site','site':json.loads((Path(__file__).resolve().parents[1]/'evaluation/site-v1.json').read_text())}}
    job,_=request('/operations/jobs',payload);ident=job['id']
    duplicate,_=request('/operations/jobs',payload);assert duplicate['id']==ident
    deadline=time.monotonic()+90
    while time.monotonic()<deadline:
        job,trace=request('/operations/jobs/'+ident)
        if job['status'] not in {'queued','running'}:break
        time.sleep(.2)
    assert job['status']=='completed',job
    assert job['result']['summary']['status']=='completed'
    graph,_=request('/operations/graph');assert any(n['kind']=='asset' for n in graph['nodes'])
    knowledge,_=request('/operations/knowledge',{'question':'How are concurrent SQLite event sequence numbers allocated?'})
    assert knowledge['sources']
    metrics,_=request('/operations/metrics');assert metrics['routes']
    output.mkdir(parents=True,exist_ok=False)
    for name,value in [('site-job',job),('graph',graph),('answer',knowledge),('metrics',metrics)]:
        (output/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')
    result={'passed':True,'job_id':ident,'idempotency_verified':True,'site_status':job['result']['summary']['status'],
            'events':len(job['result']['telemetry']),'trace_id':trace,'graph_nodes':len(graph['nodes']),'identity':identity}
    (output/'summary.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:8013');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    print(json.dumps(run(a.url,a.output),indent=2))
