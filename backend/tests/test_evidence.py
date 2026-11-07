import json
from pathlib import Path
import zipfile
import pytest
from backend.experiments.evidence import bundle_evidence, verify_archive


def test_evidence_roundtrip_preserves_binary_and_logs(tmp_path):
    source = tmp_path / 'remote'; source.mkdir()
    (source / 'log.txt').write_text('real transcript\n')
    (source / 'data.bin').write_bytes(bytes(range(256)))
    archive = tmp_path / 'remote.zip'
    bundle_evidence(source, archive, True)
    result = verify_archive(archive, tmp_path / 'local', require_passed=False)
    assert result['integrity_verified']
    assert result['all_validation_gates_passed'] is None
    assert (tmp_path / 'local/data.bin').read_bytes() == bytes(range(256))
    assert (tmp_path / 'local/LOCAL_RECEIPT.json').exists()


def test_partial_evidence_cannot_authorize_shutdown(tmp_path):
    source = tmp_path / 'source'; source.mkdir()
    archive = tmp_path / 'partial.zip'
    bundle_evidence(source, archive, False)
    with pytest.raises(ValueError, match='incomplete'):
        verify_archive(archive, tmp_path / 'local', require_passed=False)
    assert not (tmp_path / 'local').exists()


def test_corrupt_evidence_has_no_local_receipt(tmp_path):
    source = tmp_path / 'source'; source.mkdir()
    (source / 'results.json').write_text('{}')
    archive = tmp_path / 'remote.zip'; bundle_evidence(source, archive, True)
    with zipfile.ZipFile(archive) as z:
        files = {n: z.read(n) for n in z.namelist()}
    files['results.json'] = b'{"forged":true}'
    with zipfile.ZipFile(archive, 'w') as z:
        for name, raw in files.items(): z.writestr(name, raw)
    with pytest.raises(ValueError, match='checksum'):
        verify_archive(archive, tmp_path / 'local', require_passed=False)
    assert not (tmp_path / 'local').exists()


def test_archive_path_traversal_rejected(tmp_path):
    archive = tmp_path / 'unsafe.zip'
    with zipfile.ZipFile(archive, 'w') as z:
        z.writestr('../escape.txt', 'x')
    with pytest.raises(ValueError, match='path'):
        verify_archive(archive, tmp_path / 'local', require_passed=False)
    assert not (tmp_path / 'escape.txt').exists()


def test_completed_bundle_without_validation_results_rejected(tmp_path):
    source = tmp_path / 'source'; source.mkdir()
    (source / 'session.json').write_text(json.dumps({'status':'completed','steps':[]}))
    archive = tmp_path / 'remote.zip'; bundle_evidence(source, archive, True)
    with pytest.raises(ValueError, match='step set'):
        verify_archive(archive, tmp_path / 'local')


def _complete_fixture(folder):
    from backend.experiments.evidence import sha256
    folder.mkdir()
    steps = ['preflight','install','tests','contracts','baseline','repeat','usd','inference',
             'agent_evaluation','isaac_install','isaac_smoke','inference_freeze','isaac_freeze']
    def save(name, value):
        path = folder / name; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))
    for name in steps: (folder / (name + '.log')).write_text('fixture log\n')
    (folder / 'source.tar.gz').write_bytes(b'fixture source, not production evidence')
    save('session.json', {'status':'completed','model':'fixture-model','revision':'a'*40,
                         'steps':[{'name':n,'exit_code':0} for n in steps]})
    (folder / 'tests.xml').write_text('<testsuites><testsuite tests="58" failures="0" errors="0" skipped="0"/></testsuites>')
    save('contracts.json', {'passed':True})
    save('agent-evaluation.json', {'passed':True,'completed_cases':3,'total_cases':3})
    save('inference.json', {'validated':True,'model_id':'fixture-model','revision':'a'*40})
    for name in ['baseline','repeat']:
        save(name + '/report.json', {'status':'completed','evaluation_passed':True,
                                    'request':{'seed':42},'summary':{'total_scenarios':100}})
    save('repeat/comparison.json', {'reproduced':True})
    stage = b'#usda 1.0\n'
    (folder / 'warehouse.usda').write_bytes(stage)
    save('isaac-smoke.json', {'passed':True,'steps':120,'probe_final_z':.1,'stage_sha256':sha256(stage)})


def test_all_gates_required_for_verified_local_receipt(tmp_path):
    remote = tmp_path / 'remote'; _complete_fixture(remote)
    archive = tmp_path / 'remote.zip'; bundle_evidence(remote, archive, True)
    receipt = verify_archive(archive, tmp_path / 'local')
    assert receipt['all_validation_gates_passed'] is True
    assert receipt['verified_file_count'] > 20


def test_missing_raw_logs_rejected_even_with_passing_summary(tmp_path):
    remote = tmp_path / 'remote'; _complete_fixture(remote)
    (remote / 'isaac_smoke.log').unlink()
    archive = tmp_path / 'remote.zip'; bundle_evidence(remote, archive, True)
    with pytest.raises(ValueError, match='Raw logs'):
        verify_archive(archive, tmp_path / 'local')
