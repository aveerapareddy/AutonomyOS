"""Synthetic fixtures exercise verifier rejection contracts, not live-run claims."""
import hashlib
import json
from pathlib import Path
import zipfile
import pytest
from scripts.verify_cpu_evidence import verify


def make_bundle(path,unsafe=False,failed=False,tampered=False):
    ready={'passed':True,'public_demo':True,'operator_routes_blocked':True,'restart_verified':True,'revision':'fixture',
           'http_smoke':{'passed':True},'restart_smoke':{'restart_verified':True}}
    files={'ready.json':json.dumps(ready).encode(),'junit.xml':f'<testsuite tests="164" errors="0" failures="{1 if failed else 0}" skipped="0"/>'.encode()}
    if unsafe:files['../escape']=b'unsafe'
    manifest={'files':{name:{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()} for name,raw in files.items()}}
    with zipfile.ZipFile(path,'w') as archive:
        archive.writestr('manifest.json',json.dumps(manifest))
        for name,raw in files.items():archive.writestr(name,raw+b'x' if tampered and name=='junit.xml' else raw)


def test_cpu_verifier_rejects_paths_failed_tests_and_tampering(tmp_path):
    for name,kwargs in [('unsafe',{'unsafe':True}),('failed',{'failed':True}),('tampered',{'tampered':True})]:
        path=tmp_path/(name+'.zip');make_bundle(path,**kwargs)
        with pytest.raises(ValueError):verify(path,tmp_path/(name+'-out'))


def test_cpu_verifier_accepts_consistent_synthetic_contract(tmp_path):
    path=tmp_path/'fixture.zip';make_bundle(path)
    receipt=verify(path,tmp_path/'verified')
    assert receipt['gates_passed'] and receipt['integrity_verified']
