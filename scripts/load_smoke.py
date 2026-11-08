"""Small measured HTTP concurrency smoke; not a production capacity benchmark."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import statistics
import time
import urllib.request

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:8013');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    def one(_):
        start=time.perf_counter()
        with urllib.request.urlopen(a.url+'/health',timeout=15) as response:
            return {'status':response.status,'seconds':time.perf_counter()-start,'trace_id':response.headers.get('X-Trace-ID')}
    start=time.perf_counter()
    with ThreadPoolExecutor(max_workers=8) as pool:rows=list(pool.map(one,range(100)))
    elapsed=time.perf_counter()-start;values=sorted(r['seconds'] for r in rows)
    report={'passed':all(r['status']==200 for r in rows),'requests':100,'concurrency':8,'elapsed_seconds':elapsed,
            'requests_per_second':100/elapsed,'median_seconds':statistics.median(values),'p95_seconds':values[94],'maximum_seconds':max(values),'rows':rows,
            'limitations':['Health-route HTTP smoke on one local host, not simulator throughput or a production SLO.']}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))
