"""Exercise an actual CPU demo HTTP server; never substitutes a recorded result."""
import argparse
import json
from pathlib import Path
import re
import urllib.request
import urllib.error


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8000')
    parser.add_argument('--mission-file', type=Path, required=True)
    parser.add_argument('--verify-restart', action='store_true')
    args = parser.parse_args()
    base = args.url.rstrip('/')

    def request(path, body=None):
        raw = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(base + path, data=raw, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=120) as response:
            assert response.status == 200 or response.status == 201
            return json.load(response)

    assert request('/health')['status'] == 'ok'
    with urllib.request.urlopen(base + '/demo/', timeout=10) as response:
        html = response.read().decode()
        assert '<base href="/demo/">' in html
        scripts = re.findall(r'<script[^>]+src="([^"]+)"', html)
        assert scripts
    for script in scripts:
        with urllib.request.urlopen(base + '/demo/' + script, timeout=10) as response:
            assert response.status == 200
    if args.verify_restart:
        mission_id = args.mission_file.read_text().strip()
    else:
        mission_id = request('/missions', {'mission_text': 'Navigate to target'})['mission_id']
        summary = request(f'/missions/{mission_id}/execute', {})
        assert summary['execution_status'] == 'completed', summary
        args.mission_file.parent.mkdir(parents=True, exist_ok=True)
        args.mission_file.write_text(mission_id)
    assert request(f'/missions/{mission_id}')['mission_id'] == mission_id
    telemetry = request(f'/missions/{mission_id}/telemetry')
    assert any(e['event_type'] == 'robot_state' and e['payload']['backend'] == 'pybullet' for e in telemetry['events'])
    assert [e['sequence'] for e in telemetry['events']] == list(range(1, telemetry['count'] + 1))
    replay = request(f'/missions/{mission_id}/replay')
    assert replay['frame_count'] == telemetry['count']
    assert request(f'/missions/{mission_id}/telemetry?after_sequence={telemetry["count"]}')['count'] == 0
    try:
        request('/benchmarks/run', {'benchmark_name': 'public-smoke', 'scenario_count': 1})
        raise AssertionError('Public batch route was not blocked')
    except urllib.error.HTTPError as exc:
        assert exc.code == 403
    print(json.dumps({'passed': True, 'mission_id': mission_id, 'events': telemetry['count'], 'restart_verified': args.verify_restart}))


if __name__ == '__main__':
    main()
