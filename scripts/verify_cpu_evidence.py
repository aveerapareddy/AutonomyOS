"""Independently verify a copied CPU-demo bundle before temporary storage shutdown."""
import argparse
import hashlib
import json
from pathlib import Path,PurePosixPath
import xml.etree.ElementTree as ET
import zipfile


def verify(archive,output):
    with zipfile.ZipFile(archive) as z:
        infos=z.infolist();names=[f.filename for f in infos]
        if len(names)!=len(set(names)) or len(names)>100 or sum(f.file_size for f in infos)>30_000_000:raise ValueError('Unsafe or oversized archive')
        for name in names:
            path=PurePosixPath(name)
            if path.is_absolute() or '..' in path.parts or '\\' in name or path.as_posix()!=name:raise ValueError('Unsafe member path')
        manifest=json.loads(z.read('manifest.json'))
        if set(names)!={'manifest.json',*manifest['files']}:raise ValueError('Manifest member mismatch')
        for name,record in manifest['files'].items():
            raw=z.read(name)
            if len(raw)!=record['bytes'] or hashlib.sha256(raw).hexdigest()!=record['sha256']:raise ValueError('Artifact integrity mismatch')
        ready=json.loads(z.read('ready.json'))
        if not all(ready.get(k) is True for k in ['passed','public_demo','operator_routes_blocked','restart_verified']):raise ValueError('CPU demo validation gate failed')
        junit=ET.fromstring(z.read('junit.xml'));suites=[junit] if junit.tag=='testsuite' else list(junit.iter('testsuite'))
        tests=sum(int(s.get('tests',0)) for s in suites)
        if tests<164 or any(int(s.get(k,0)) for s in suites for k in ['errors','failures','skipped']):raise ValueError('CPU test gate failed')
        if not ready['http_smoke']['passed'] or not ready['restart_smoke']['restart_verified']:raise ValueError('Restart/HTTP smoke failed')
        output.mkdir(parents=True,exist_ok=False);z.extractall(output)
    result={'integrity_verified':True,'gates_passed':True,'file_count':len(manifest['files']),'tests':tests,
            'revision':ready['revision'],'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}
    (output/'LOCAL_RECEIPT.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('archive',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(verify(a.archive,a.output),indent=2))
