"""Public demo resource policy and request tracing."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.demo_guard import DemoGuard


def demo_client():
    app = FastAPI()
    app.add_middleware(DemoGuard, public_demo=True)

    @app.post('/missions')
    def create():
        return {'ok': True}

    @app.post('/benchmarks/run')
    def benchmark():
        raise AssertionError('Public batch route must never execute')

    return TestClient(app)


def test_public_demo_blocks_batches_and_large_declared_bodies():
    client = demo_client()
    assert client.post('/benchmarks/run').status_code == 403
    assert client.post('/missions', content='x' * 16385).status_code == 413
    assert client.post('/missions', headers={'content-length': 'invalid'}).status_code == 400


def test_public_demo_creation_quota_and_trace_headers():
    client = demo_client()
    for _ in range(20):
        response = client.post('/missions')
        assert response.status_code == 200
        assert len(response.headers['X-Request-ID']) == 32
        assert response.headers['X-Content-Type-Options'] == 'nosniff'
    response = client.post('/missions')
    assert response.status_code == 429
    assert response.headers['Retry-After'] == '60'


def test_public_demo_blocks_all_operator_workflow_paths():
    client=demo_client()
    for path in ['/workflows','/workflows/import','/workflows/example/approve']:
        assert client.post(path).status_code==403
