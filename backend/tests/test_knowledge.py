import json
from pathlib import Path
import pytest
from backend.knowledge.retrieval import EngineeringIndex, evaluate, sha

ROOT=Path(__file__).resolve().parents[2]


def test_versioned_citations_match_exact_source():
    index=EngineeringIndex(ROOT,ROOT/'knowledge/engineering-v2.json')
    hit=index.search('concurrent SQLite sequence allocation')[0]
    assert hit['document_id']=='journal'
    source=ROOT/hit['citation']['path']
    assert sha(source.read_bytes())==hit['citation']['source_sha256']
    assert hit['excerpt']=='\n'.join(source.read_text().splitlines()[hit['citation']['start_line']-1:hit['citation']['end_line']])


def test_stale_source_rejected(tmp_path):
    source=tmp_path/'source.py';source.write_text('original\n')
    doc={'id':'x','title':'x','path':'source.py','source_sha256':sha(source.read_bytes()),
         'start_line':1,'end_line':1,'excerpt':'original'}
    manifest=tmp_path/'manifest.json';manifest.write_text(json.dumps({'schema_version':1,'documents':[doc]}))
    source.write_text('changed\n')
    with pytest.raises(ValueError,match='Stale source'):
        EngineeringIndex(tmp_path,manifest)


def test_unanswerable_query_does_not_invent_citation():
    index=EngineeringIndex(ROOT,ROOT/'knowledge/engineering-v2.json')
    assert index.search('zzzzqwertyuiop')==[]
    with pytest.raises(ValueError): index.search('x',11)
    with pytest.raises(ValueError): evaluate(index,[{'id':'bad','query':'x','relevant':['unknown']}])


def test_citation_tamper_and_path_escape_rejected(tmp_path):
    corpus=json.loads((ROOT/'knowledge/engineering-v2.json').read_text())
    corpus['documents'][0]['excerpt']='forged source'
    manifest=tmp_path/'tamper.json';manifest.write_text(json.dumps(corpus))
    with pytest.raises(ValueError,match='mismatch'): EngineeringIndex(ROOT,manifest)
    corpus['documents'][0]['path']='../outside.py'
    manifest.write_text(json.dumps(corpus))
    with pytest.raises(ValueError,match='Unsafe'): EngineeringIndex(ROOT,manifest)
