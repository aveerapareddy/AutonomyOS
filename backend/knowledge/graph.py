"""Derived engineering relationship graph with artifact provenance; no inferred facts."""
from pathlib import Path
from backend.operations.jobs import JobStore

def build_graph(store:JobStore):
    nodes={};edges=[]
    def node(ident,kind,label,**data):nodes[ident]={'id':ident,'kind':kind,'label':label,**data}
    def edge(a,b,relation):edges.append({'source':a,'target':b,'relation':relation})
    for row in store.list():
        job=store.get(row['id']);ident='job:'+job['id']
        node(ident,'job',job['id'][:8],status=job['status'],input_hash=job['input_hash'])
        result=job['result']
        if not result:continue
        if result['kind']=='site':
            site_id='site:'+result['site_hash'];site=result['site']
            node(site_id,'site',site['name'],site_hash=result['site_hash']);edge(ident,site_id,'simulates')
            for asset in site['assets']:
                asset_id=site_id+':'+asset['id'];node(asset_id,'asset',asset['id'],position=[asset['x'],asset['y']],kind_label=asset['kind']);edge(site_id,asset_id,'contains')
            if result['summary']['status']!='completed':
                failure=ident+':failure';node(failure,'failure',result['summary'].get('message') or 'Mission failed');edge(ident,failure,'observed')
        else:
            report=result['report'];seed_id='seed:'+str(report['request']['seed'])
            node(seed_id,'seed',str(report['request']['seed']));edge(ident,seed_id,'uses_seed')
            for scenario in report['summary']['scenario_results']:
                sid=ident+':'+scenario['scenario_id'];node(sid,'scenario',scenario['scenario_name'],success=scenario['success']);edge(ident,sid,'evaluates')
                if not scenario['success']:
                    failure=sid+':failure';node(failure,'failure',scenario.get('message') or 'Task incomplete');edge(sid,failure,'observed')
    return {'nodes':list(nodes.values()),'edges':edges,'provenance':'Derived from persisted job inputs and simulator results; relationships are not causal diagnoses.'}
