"""Portable evidence bundles and independent local verification. Standard library only."""
import base64
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile
import xml.etree.ElementTree as ET


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def bundle_evidence(folder: Path, destination: Path, complete: bool):
    files = {}
    for path in sorted(folder.rglob('*')):
        if path.is_file() and path.name != 'manifest.json':
            if path.is_symlink():
                raise ValueError('Symlinks are not evidence files')
            data = path.read_bytes()
            files[path.relative_to(folder).as_posix()] = {'sha256': sha256(data), 'bytes': len(data)}
    manifest = {'schema_version': 1, 'complete': complete, 'files': files}
    (folder / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    temporary = destination.with_suffix('.partial')
    with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in [*files, 'manifest.json']:
            archive.write(folder / name, name)
    temporary.replace(destination)
    envelope = {'schema_version': 1, 'archive_sha256': sha256(destination.read_bytes()),
                'archive_base64': base64.b64encode(destination.read_bytes()).decode()}
    text = destination.with_suffix('.transfer.txt')
    temp_text = text.with_suffix('.partial')
    temp_text.write_text(json.dumps(envelope))
    temp_text.replace(text)
    return manifest


def verify_archive(archive_path: Path, extract_to: Path, require_passed=True):
    """Never create a receipt or extract data until archive integrity and gates pass."""
    if extract_to.exists():
        raise FileExistsError(extract_to)
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate archive member')
        for info in archive.infolist():
            path = PurePosixPath(info.filename)
            if path.is_absolute() or '..' in path.parts or '\\' in info.filename or info.is_dir():
                raise ValueError('Invalid archive member path')
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Archive symlink rejected')
        if sum(i.file_size for i in archive.infolist()) > 200_000_000:
            raise ValueError('Evidence archive is too large')
        manifest = json.loads(archive.read('manifest.json'))
        if not manifest['complete']:
            raise ValueError('Session evidence is incomplete')
        expected = set(manifest['files']) | {'manifest.json'}
        if set(names) != expected:
            raise ValueError('Unexpected or missing archive member')
        data = {}
        for name, expected_file in manifest['files'].items():
            raw = archive.read(name)
            if sha256(raw) != expected_file['sha256'] or len(raw) != expected_file['bytes']:
                raise ValueError('Evidence checksum mismatch: ' + name)
            data[name] = raw
        passed = None
        if require_passed:
            def read_json(name): return json.loads(data[name])
            session = read_json('session.json')
            if session['status'] != 'completed' or any(s['exit_code'] != 0 for s in session['steps']):
                raise ValueError('A validation step failed')
            required_steps = {'preflight', 'install', 'tests', 'contracts', 'baseline', 'repeat',
                              'usd', 'inference', 'agent_evaluation', 'isaac_install', 'isaac_smoke',
                              'inference_freeze', 'isaac_freeze'}
            if set(s['name'] for s in session['steps']) != required_steps:
                raise ValueError('Validation step set is incomplete')
            if not all(name + '.log' in data for name in required_steps) or not data.get('source.tar.gz'):
                raise ValueError('Raw logs or source snapshot are missing')
            inference = read_json('inference.json')
            if inference['model_id'] != session['model'] or inference['revision'] != session['revision']:
                raise ValueError('Model identity differs from the session')
            suites = list(ET.fromstring(data['tests.xml']).iter('testsuite'))
            if not suites or sum(int(s.attrib.get('tests', 0)) for s in suites) < 58:
                raise ValueError('Expected test suite was not executed')
            if any(int(s.attrib.get(k, 0)) for s in suites for k in ('failures', 'errors', 'skipped')):
                raise ValueError('Tests failed or were skipped')
            for name in ('contracts.json', 'agent-evaluation.json', 'isaac-smoke.json'):
                if read_json(name)['passed'] is not True:
                    raise ValueError('Evaluation failed: ' + name)
            if not inference['validated']:
                raise ValueError('Model proposal failed validation')
            if read_json('agent-evaluation.json')['completed_cases'] != read_json('agent-evaluation.json')['total_cases']:
                raise ValueError('Incomplete model evaluation')
            for directory in ('baseline', 'repeat'):
                result = read_json(directory + '/report.json')
                if result['status'] != 'completed' or not result['evaluation_passed']:
                    raise ValueError('Simulation evaluation failed')
                if result['summary']['total_scenarios'] != 100 or result['request']['seed'] != 42:
                    raise ValueError('Unexpected benchmark inputs')
            comparison = read_json('repeat/comparison.json')
            if comparison['reproduced'] is not True:
                raise ValueError('Semantic repeat comparison failed')
            smoke = read_json('isaac-smoke.json')
            if smoke['stage_sha256'] != sha256(data['warehouse.usda']):
                raise ValueError('Isaac stage does not match exported geometry')
            if smoke['steps'] != 120 or not .05 < smoke['probe_final_z'] < .2:
                raise ValueError('Isaac probe result outside contract')
            passed = True
        extract_to.mkdir(parents=True)
        for name, raw in data.items():
            target = extract_to / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        (extract_to / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    receipt = {'archive_sha256': sha256(archive_path.read_bytes()), 'verified_file_count': len(data),
               'all_validation_gates_passed': passed, 'integrity_verified': True}
    (extract_to / 'LOCAL_RECEIPT.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt
