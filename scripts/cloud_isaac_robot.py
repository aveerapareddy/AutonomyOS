"""Run the optional advanced Isaac test alongside an already-validated CPU demo."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--cpu-python',required=True);p.add_argument('--isaac-env',type=Path,required=True);p.add_argument('--accept-isaac-eula',action='store_true');a=p.parse_args()
    if not a.accept_isaac_eula:p.error('Explicit Omniverse license approval is required')
    root=Path(__file__).resolve().parents[1];out=a.evidence.resolve();out.mkdir(parents=True,exist_ok=True);env_dir=a.isaac_env.resolve()
    stages=[]
    def step(name,command,timeout=1200,env=None):
        start=time.monotonic()
        with (out/(name+'.log')).open('wb') as log:
            process=subprocess.Popen(command,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            try:code=process.wait(timeout)
            except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait();code=124
        stages.append({'name':name,'exit_code':code,'elapsed_seconds':time.monotonic()-start})
        (out/'isaac-stages.json').write_text(json.dumps(stages,indent=2)+'\n')
        print(json.dumps(stages[-1]),flush=True)
        if code:raise RuntimeError('Advanced Isaac stage failed: '+name)
    try:
        step('gpu-preflight',['nvidia-smi'])
        step('site-usd',[a.cpu_python,'-m','scripts.export_site_usd','--site','evaluation/site-v1.json','--output',str(out/'site.usda')])
        step('isaac-venv',['uv','venv','--python','3.12','--seed',str(env_dir)])
        python=str(env_dir/'bin/python')
        step('isaac-install',[python,'-m','pip','install','isaacsim[all,extscache]==6.2.0.0','--extra-index-url','https://pypi.nvidia.com','Pillow==12.1.1'],1800)
        step('isaac-robot',[python,'-m','scripts.run_isaac_robot','--stage',str(out/'site.usda'),'--output',str(out/'isaac-robot')],1200,
             {**os.environ,'OMNI_KIT_ACCEPT_EULA':'YES','OMNI_KIT_ALLOW_ROOT':'1'})
        step('isaac-freeze',[python,'-m','pip','freeze'])
    finally:
        (out/'isaac-stages.json').write_text(json.dumps(stages,indent=2)+'\n')
