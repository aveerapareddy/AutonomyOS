"""Validate a temporary CPU deployment using previously built, hash-verified assets."""
import argparse
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import signal
import sqlite3
import subprocess
import sys
import tarfile
import time
import urllib.request,urllib.error
from scripts.package_frontend import frontend_source_hash

ROOT=Path(__file__).resolve().parents[1]

def run(output,python,archive,manifest):
    output.mkdir(parents=True,exist_ok=False);metadata=json.loads(manifest.read_text())
    if metadata['frontend_source_hash']!=frontend_source_hash(ROOT):raise ValueError('Built frontend does not match source')
    if metadata['archive_sha256']!=hashlib.sha256(archive.read_bytes()).hexdigest():raise ValueError('Frontend archive checksum mismatch')
    dist=output/'dashboard';dist.mkdir()
    with tarfile.open(archive) as tar:
        members=tar.getmembers()
        for item in members:
            path=PurePosixPath(item.name)
            if path.is_absolute() or '..' in path.parts or not item.isfile():raise ValueError('Unsafe frontend archive')
        tar.extractall(dist,filter='data')
    for name,expected in metadata['files'].items():
        if hashlib.sha256((dist/name).read_bytes()).hexdigest()!=expected:raise ValueError('Browser asset hash mismatch')
    (output/'frontend-manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')
    env={**os.environ,'AUTONOMY_PUBLIC_DEMO':'true','AUTONOMY_DATABASE_PATH':str(output/'missions.sqlite3'),
         'AUTONOMY_FRONTEND_DIRECTORY':str(dist),'AUTONOMY_TRACES_DIRECTORY':str(output/'traces'),
         'AUTONOMY_OPERATOR_TOKEN':'','AUTONOMY_OPERATOR_ACCOUNTS_JSON':'[]','AUTONOMY_WORKFLOW_DIRECTORY':'',
         'AUTONOMY_OPERATIONS_DIRECTORY':'','AUTONOMY_PLANNER_MODE':'rule_based'}
    def command(name,args,stage_env=None):
        with (output/(name+'.log')).open('wb') as log:r=subprocess.run(args,cwd=ROOT,env=stage_env or env,stdout=log,stderr=subprocess.STDOUT,timeout=900)
        if r.returncode:raise RuntimeError(name+' failed')
    uv='/usr/local/bin/uv'
    if not Path(uv).exists():uv='uv'
    command('dependencies',[uv,'pip','install','--python',python,'-r','backend/requirements-demo.txt','-r','requirements-usd.txt','pytest'])
    command('tests',[python,'-m','pytest','backend/tests','-q','--junitxml='+str(output/'junit.xml')],{**env,'AUTONOMY_PUBLIC_DEMO':'false','AUTONOMY_DATABASE_PATH':'','AUTONOMY_TRACES_DIRECTORY':''})
    command('freeze',[uv,'pip','freeze','--python',python])
    command('source',['git','archive','--format=tar.gz','--output='+str(output/'source.tar.gz'),'HEAD'])
    def start():
        log=(output/'server.log').open('ab');process=subprocess.Popen([python,'-m','uvicorn','backend.api.main:app','--host','0.0.0.0','--port','8000'],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        for _ in range(100):
            if process.poll() is not None:raise RuntimeError('Demo process exited')
            try:
                if urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=2).status==200:return process
            except Exception:pass
            time.sleep(.2)
        raise RuntimeError('Demo readiness timeout')
    process=start();command('http-smoke',[python,'scripts/smoke_demo.py','--mission-file',str(output/'mission-id.txt')])
    process.send_signal(signal.SIGTERM);process.wait(20);process=start()
    command('restart-smoke',[python,'scripts/smoke_demo.py','--mission-file',str(output/'mission-id.txt'),'--verify-restart'])
    for path in ['/operations/identity','/workflows']:
        try:urllib.request.urlopen('http://127.0.0.1:8000'+path,timeout=5);raise AssertionError('Operator exposed')
        except urllib.error.HTTPError as error:
            if error.code!=403:raise
    result={'passed':True,'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
      'frontend_source_hash':metadata['frontend_source_hash'],'frontend_archive_sha256':metadata['archive_sha256'],
      'server_pid':process.pid,'mission_id':(output/'mission-id.txt').read_text().strip(),'public_demo':True,
      'operator_routes_blocked':True,'restart_verified':True,'http_smoke':json.loads((output/'http-smoke.log').read_text()),
      'restart_smoke':json.loads((output/'restart-smoke.log').read_text())}
    (output/'ready.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--python',required=True);p.add_argument('--archive',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);a=p.parse_args()
    try:print(json.dumps(run(a.output.resolve(),a.python,a.archive,a.manifest),indent=2))
    except Exception as exc:
        a.output.mkdir(parents=True,exist_ok=True);(a.output/'failure.json').write_text(json.dumps({'error':str(exc)})+'\n');raise
