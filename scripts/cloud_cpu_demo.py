"""Temporary CPU demo setup and validation. Run only in an authorized disposable pod.

Never installs credentials or enables operator routes. A separate pod-stop watchdog
must be started first; archive locally before stopping temporary storage.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1]

def run(output):
    output.mkdir(parents=True,exist_ok=False)
    def command(name,args,cwd=ROOT,env=None):
        with (output/(name+'.log')).open('wb') as log:
            result=subprocess.run(args,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=1200)
        if result.returncode:raise RuntimeError(f'{name} failed; inspect log')
    command('uv-install',[sys.executable,'-m','pip','install','uv==0.9.9'])
    uv=shutil.which('uv')
    command('python-environment',[uv,'venv','--python','3.11',str(output/'venv')])
    python=str(output/'venv/bin/python')
    command('dependencies',[uv,'pip','install','--python',python,'-r',str(ROOT/'backend/requirements-demo.txt'),'-r',str(ROOT/'requirements-usd.txt'),'pytest'])
    version='20.20.2';filename=f'node-v{version}-linux-x64.tar.xz';base=f'https://nodejs.org/dist/v{version}/'
    checksum=urllib.request.urlopen(base+'SHASUMS256.txt',timeout=30).read().decode()
    expected=next(line.split()[0] for line in checksum.splitlines() if line.split()[-1]==filename)
    archive=output/filename;urllib.request.urlretrieve(base+filename,archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=expected:raise RuntimeError('Node archive SHA256 mismatch')
    # Official Node archive contains a fixed top-level directory, no untrusted user archive.
    command('node-unpack',['tar','-xJf',str(archive),'-C',str(output)])
    node_bin=output/f'node-v{version}-linux-x64/bin';env={**os.environ,'PATH':str(node_bin)+os.pathsep+os.environ['PATH'],'AUTONOMY_PLANNER_MODE':'rule_based'}
    command('frontend-install',[str(node_bin/'npm'),'ci'],ROOT/'frontend/autonomy-dashboard',env)
    command('frontend-build',[str(node_bin/'npm'),'run','build','--','--base-href','/demo/'],ROOT/'frontend/autonomy-dashboard',env)
    command('tests',[python,'-m','pytest','backend/tests','-q','--junitxml='+str(output/'junit.xml')],env=env)
    command('freeze',[uv,'pip','freeze','--python',python],env=env)
    command('source',['git','archive','--format=tar.gz','--output='+str(output/'source.tar.gz'),'HEAD'])
    env={**env,'AUTONOMY_PUBLIC_DEMO':'true','AUTONOMY_DATABASE_PATH':str(output/'missions.sqlite3'),
         'AUTONOMY_FRONTEND_DIRECTORY':str(ROOT/'frontend/autonomy-dashboard/dist/autonomy-dashboard/browser'),
         'AUTONOMY_TRACES_DIRECTORY':str(output/'traces'),'AUTONOMY_OPERATOR_TOKEN':'','AUTONOMY_OPERATOR_ACCOUNTS_JSON':'[]',
         'AUTONOMY_WORKFLOW_DIRECTORY':'','AUTONOMY_OPERATIONS_DIRECTORY':''}
    def start():
        log=(output/'server.log').open('ab')
        process=subprocess.Popen([python,'-m','uvicorn','backend.api.main:app','--host','0.0.0.0','--port','8000'],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        for _ in range(100):
            if process.poll() is not None:raise RuntimeError('Demo server exited')
            try:
                if urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=2).status==200:return process
            except Exception:pass
            time.sleep(.2)
        raise RuntimeError('Demo readiness timeout')
    process=start()
    command('http-smoke',[python,'scripts/smoke_demo.py','--mission-file',str(output/'mission-id.txt')],env=env)
    process.send_signal(signal.SIGTERM);process.wait(20)
    process=start()
    command('restart-smoke',[python,'scripts/smoke_demo.py','--mission-file',str(output/'mission-id.txt'),'--verify-restart'],env=env)
    for path in ['/operations/identity','/workflows']:
        try:urllib.request.urlopen('http://127.0.0.1:8000'+path,timeout=5);raise AssertionError('Operator route exposed')
        except urllib.error.HTTPError as error:
            if error.code!=403:raise
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    result={'passed':True,'revision':revision,'node_sha256':expected,'server_pid':process.pid,
            'mission_id':(output/'mission-id.txt').read_text().strip(),'public_demo':True,'operator_routes_blocked':True,
            'restart_verified':True,'http_smoke':json.loads((output/'http-smoke.log').read_text()),
            'restart_smoke':json.loads((output/'restart-smoke.log').read_text())}
    (output/'ready.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    try:print(json.dumps(run(a.output.resolve()),indent=2))
    except Exception as exc:
        (a.output/'failure.json').write_text(json.dumps({'error':str(exc)})+'\n');raise
