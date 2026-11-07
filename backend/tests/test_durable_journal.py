"""Durability and multi-writer ordering checks on real SQLite files."""
from concurrent.futures import ThreadPoolExecutor

from backend.schemas.mission import MissionRequest
from backend.services.mission_service import MissionService
from backend.services.replay_service import ReplayService
from backend.services.telemetry_service import TelemetryService
from backend.storage.sqlite_journal import SQLiteJournal


def test_mission_and_replay_survive_reopen(tmp_path):
    path = str(tmp_path / 'state.sqlite3')
    journal = SQLiteJournal(path)
    mission = MissionService(journal).create(MissionRequest(mission_text='Navigate to target', world_id='test'))
    TelemetryService(journal).record(mission.mission_id, 'robot_state', 'execution_engine', {'robot_x': 1.25, 'robot_y': -2, 'robot_theta': 0.5})
    reopened = SQLiteJournal(path)
    assert MissionService(reopened).get(mission.mission_id).mission_text == 'Navigate to target'
    replay = ReplayService(TelemetryService(reopened)).build_replay(mission.mission_id)
    assert replay.frames[0].robot_position == {'x': 1.25, 'y': -2, 'theta': 0.5}


def test_independent_writers_allocate_unique_sequences(tmp_path):
    path = str(tmp_path / 'state.sqlite3')
    writers = [TelemetryService(SQLiteJournal(path)) for _ in range(4)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda i: writers[i % 4].record('mission', 'robot_state', 'test', {'i': i}), range(100)))
    events = SQLiteJournal(path).events('mission')
    assert [e.sequence for e in events] == list(range(1, 101))
    assert len({e.payload['i'] for e in events}) == 100
    assert len(SQLiteJournal(path).events('mission', after_sequence=90)) == 10
