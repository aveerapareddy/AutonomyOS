"""Create a small CPU-demo evidence envelope; excludes environments and model files."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import sqlite3
import zipfile

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    root=a.source.resolve();a.output.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(root/'missions.sqlite3') as src,sqlite3.connect(root/'missions-backup.sqlite3') as dst:src.backup(dst)
    files=[f for f in root.glob('*.log') if f.is_file()]
    files += [root/n for n in ['source.tar.gz','junit.xml','ready.json','missions-backup.sqlite3']]
    files += [root/'frontend-manifest.json'] if (root/'frontend-manifest.json').exists() else []
    files += list((root/'traces').glob('*.jsonl'))
    files += [f for folder in root.glob('isaac-robot*') if folder.is_dir() for f in folder.rglob('*') if f.is_file()]
    files += [root/n for n in ['isaac-verified.json','isaac-source.tar.gz','isaac-source.json'] if (root/n).exists()]
    files += [root/'site.usda'] if (root/'site.usda').exists() else []
    files += [root/'isaac-stages.json'] if (root/'isaac-stages.json').exists() else []
    manifest={'schema_version':1,'files':{str(f.relative_to(root)):{'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size} for f in sorted(files)}}
    with zipfile.ZipFile(a.output,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('manifest.json',json.dumps(manifest,indent=2))
        for f in files:z.write(f,f.relative_to(root))
    raw=a.output.read_bytes();envelope={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'base64':base64.b64encode(raw).decode()}
    a.output.with_suffix('.json').write_text(json.dumps(envelope)+'\n')
    print(json.dumps({'archive_sha256':envelope['sha256'],'bytes':len(raw),'files':len(files)}))
