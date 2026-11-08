"""Package already-built portable browser assets with source and content hashes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile


def frontend_source_hash(root):
    files={}
    for path in sorted((root/'frontend/autonomy-dashboard').rglob('*')):
        if not path.is_file() or any(p in {'node_modules','dist','.angular'} for p in path.relative_to(root/'frontend/autonomy-dashboard').parts):continue
        files[str(path.relative_to(root))]=hashlib.sha256(path.read_bytes()).hexdigest()
    return hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();root=Path(__file__).resolve().parents[1]
    dist=root/'frontend/autonomy-dashboard/dist/autonomy-dashboard/browser'
    manifest={'revision':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'frontend_source_hash':frontend_source_hash(root),
              'files':{str(f.relative_to(dist)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(dist.rglob('*')) if f.is_file()}}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with tarfile.open(a.output,'w:gz') as tar:
        for file in sorted(dist.rglob('*')):
            if file.is_file():tar.add(file,arcname=str(file.relative_to(dist)))
    manifest['archive_sha256']=hashlib.sha256(a.output.read_bytes()).hexdigest()
    a.output.with_suffix('.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'archive_bytes':a.output.stat().st_size,'sha256':manifest['archive_sha256'],'frontend_source_hash':manifest['frontend_source_hash']}))
