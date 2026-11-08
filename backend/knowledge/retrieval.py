"""Deterministic BM25 retrieval with exact, hash-verified repository citations."""
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower().replace('_', ' '))


class EngineeringIndex:
    def __init__(self, root: Path, manifest: Path):
        self.root = root.resolve()
        raw = manifest.read_bytes()
        self.corpus_hash = sha(raw)
        corpus = json.loads(raw)
        if corpus['schema_version'] != 1:
            raise ValueError('Unsupported corpus version')
        self.documents = corpus['documents']
        if not self.documents or len(self.documents) > 100:
            raise ValueError('Corpus must contain 1..100 documents')
        self.counts = []
        seen = set()
        for doc in self.documents:
            path = (self.root / doc['path']).resolve()
            if not path.is_relative_to(self.root) or doc['id'] in seen:
                raise ValueError('Unsafe path or duplicate document ID')
            seen.add(doc['id'])
            source = path.read_bytes()
            if sha(source) != doc['source_sha256']:
                raise ValueError(f"Stale source: {doc['path']}")
            lines = source.decode().splitlines()
            start, end = doc['start_line'], doc['end_line']
            if not 1 <= start <= end <= len(lines):
                raise ValueError('Invalid citation range')
            excerpt = '\n'.join(lines[start-1:end])
            if excerpt != doc['excerpt']:
                raise ValueError('Citation excerpt mismatch')
            self.counts.append(Counter(tokens(doc['title'] + ' ' + excerpt)))
        self.average_length = sum(sum(c.values()) for c in self.counts) / len(self.counts)

    def search(self, query: str, k: int = 3) -> list[dict]:
        if not 1 <= k <= 10 or not 1 <= len(query) <= 2000:
            raise ValueError('Query/k outside bounds')
        terms = set(tokens(query))
        scores = []
        n = len(self.counts)
        for doc, counts in zip(self.documents, self.counts):
            score = 0.0
            length = sum(counts.values())
            for term in sorted(terms):
                frequency = counts[term]
                df = sum(term in c for c in self.counts)
                idf = math.log(1 + (n - df + .5) / (df + .5))
                score += idf * frequency * 2.5 / (frequency + 1.5 * (.25 + .75 * length / self.average_length))
            if score > 0:
                scores.append({'document_id':doc['id'], 'score':score,
                               'citation':{key:doc[key] for key in ('path','start_line','end_line','source_sha256')},
                               'excerpt':doc['excerpt']})
        return sorted(scores,key=lambda r:(-r['score'],r['document_id']))[:k]


def evaluate(index: EngineeringIndex, cases: list[dict], k: int = 3) -> dict:
    if not cases or len({c['id'] for c in cases}) != len(cases):
        raise ValueError('Empty or duplicate evaluation cases')
    ids = {d['id'] for d in index.documents}
    rows = []
    for case in cases:
        relevant = set(case['relevant'])
        if not relevant or not relevant <= ids:
            raise ValueError('Unknown/empty relevance labels')
        hits = index.search(case['query'], k)
        ranks = [i+1 for i,h in enumerate(hits) if h['document_id'] in relevant]
        rows.append({'id':case['id'],'query':case['query'],'relevant':sorted(relevant),
                     'recall_at_k':len(ranks)/len(relevant),'reciprocal_rank':1/min(ranks) if ranks else 0,
                     'hits':hits})
    return {'corpus_hash':index.corpus_hash,'k':k,'case_count':len(rows),
            'mean_recall_at_k':sum(r['recall_at_k'] for r in rows)/len(rows),
            'mean_reciprocal_rank':sum(r['reciprocal_rank'] for r in rows)/len(rows),'cases':rows}
