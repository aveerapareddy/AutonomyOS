"""Bounded GPU reference validation; checkpoints logs and transfer bundles per stage.

Run only on an explicitly authorized rented host. Does not stop/delete resources.
The caller must verify a local receipt before shutting the host down.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import tarfile
import time
from datetime import datetime, timezone
from backend.experiments.evidence import bundle_evidence

ROOT = Path(__file__).resolve().parents[1]
MODEL = 'nvidia/Llama-3.1-Nemotron-Nano-8B-v1'
REVISION = '54641c1611fcff44fa4865626462445e0a153fc7'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--isaac-env', type=Path, required=True)
    parser.add_argument('--accept-isaac-eula', action='store_true', help='Use only after explicit user approval')
    args = parser.parse_args()
    if not args.accept_isaac_eula:
        parser.error('Explicit Omniverse EULA approval is required for this validation')
    folder = args.evidence.resolve()
    folder.mkdir(parents=True, exist_ok=False)
    archive = folder.parent / (folder.name + '.zip')
    session = {'status': 'running', 'started_at': datetime.now(timezone.utc).isoformat(),
               'platform': platform.platform(), 'python': platform.python_version(),
               'model': MODEL, 'revision': REVISION, 'isaac_eula_approved': True,
               'steps': [], 'limitations': ['Isaac geometry/basic CPU physics smoke only; no Isaac robot navigation.',
                                          'Three labeled model prompts are not a general agent reliability benchmark.',
                                          'No NIM/Cosmos/Kubernetes deployment in this session.']}
    with tarfile.open(folder / 'source.tar.gz', 'w:gz') as source:
        for path in sorted(ROOT.rglob('*')):
            rel = path.relative_to(ROOT)
            if not path.is_file() or path.is_symlink(): continue
            if any(part in {'.git', '.venv', '__pycache__', '.pytest_cache', 'artifacts'} for part in rel.parts): continue
            if any(part.startswith('.env') for part in rel.parts): continue
            source.add(path, arcname=str(Path('AutonomyOS') / rel))

    def checkpoint(complete=False):
        (folder / 'session.json').write_text(json.dumps(session, indent=2) + '\n')
        bundle_evidence(folder, archive, complete)

    def step(name, command, timeout=600, extra_env=None):
        start = time.monotonic()
        env = {**os.environ, **(extra_env or {})}
        with (folder / (name + '.log')).open('wb') as log:
            process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log,
                                       stderr=subprocess.STDOUT, start_new_session=True)
            try:
                code = process.wait(timeout)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                code = 124
        session['steps'].append({'name': name, 'command': command, 'exit_code': code,
                                 'elapsed_seconds': time.monotonic() - start})
        checkpoint()
        print(json.dumps(session['steps'][-1]), flush=True)
        if code:
            raise RuntimeError('Validation step failed: ' + name)

    checkpoint()
    py = sys.executable
    try:
        step('preflight', [py, '-c', "import torch,subprocess; subprocess.run(['nvidia-smi'],check=True); print(torch.__version__); assert torch.cuda.is_available(); assert torch.cuda.get_device_properties(0).total_memory >= 40_000_000_000"])
        step('install', [py, '-m', 'pip', 'install', '-r', 'backend/requirements.txt', '-r',
                         'requirements-gpu-validation.txt', '-r', 'requirements-usd.txt'], 1200)
        step('tests', [py, '-m', 'pytest', 'backend/tests', '-q', '--junitxml=' + str(folder / 'tests.xml')])
        step('contracts', [py, '-m', 'scripts.run_evaluation_suite', '--output', str(folder / 'contracts.json')])
        step('baseline', [py, '-m', 'scripts.run_experiment', '--output', str(folder / 'baseline'),
                          '--ledger', str(folder / 'experiments.sqlite'), '--count', '100', '--seed', '42'])
        step('repeat', [py, '-m', 'scripts.run_experiment', '--output', str(folder / 'repeat'),
                        '--ledger', str(folder / 'experiments.sqlite'), '--count', '100', '--seed', '42',
                        '--compare', str(folder / 'baseline/report.json')])
        step('usd', [py, '-m', 'scripts.export_scenario_usd', str(folder / 'warehouse.usda')])
        step('inference', [py, '-m', 'scripts.run_hf_validation', '--model', MODEL, '--revision', REVISION,
                           '--output', str(folder / 'inference.json')])
        step('agent_evaluation', [py, '-m', 'scripts.run_agent_evaluation', '--revision', REVISION,
                                  '--output', str(folder / 'agent-evaluation.json')])
        env_py = str(args.isaac_env.resolve() / 'bin/python')
        # Installation transcript is fully captured, including venv creation and pip output.
        setup = "import subprocess,sys; subprocess.run([sys.executable,'-m','venv',sys.argv[1]],check=True); subprocess.run([sys.argv[1]+'/bin/python','-m','pip','install','--upgrade','pip'],check=True); subprocess.run([sys.argv[1]+'/bin/python','-m','pip','install','isaacsim[all,extscache]==6.2.0.0','--extra-index-url','https://pypi.nvidia.com'],check=True)"
        step('isaac_install', [py, '-c', setup, str(args.isaac_env.resolve())], 1800)
        step('isaac_smoke', [env_py, '-m', 'scripts.run_isaac_smoke', '--stage', str(folder / 'warehouse.usda'),
                             '--output', str(folder / 'isaac-smoke.json')], 600,
             {'OMNI_KIT_ACCEPT_EULA': 'YES', 'OMNI_KIT_ALLOW_ROOT': '1'})
        step('inference_freeze', [py, '-m', 'pip', 'freeze'])
        step('isaac_freeze', [env_py, '-m', 'pip', 'freeze'])
        session['status'] = 'completed'
    except Exception as exc:
        session['status'] = 'failed'
        session['error'] = {'type': type(exc).__name__, 'message': str(exc)}
    finally:
        session['finished_at'] = datetime.now(timezone.utc).isoformat()
        checkpoint(complete=True)
    print('Evidence bundle: ' + str(archive), flush=True)
    return 0 if session['status'] == 'completed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
