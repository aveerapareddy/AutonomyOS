"""Telemetry service and API tests."""

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.schemas.telemetry import TelemetryEventType
from backend.services.telemetry_service import TelemetryService

client = TestClient(app)


def test_telemetry_service_records_events() -> None:
    """Recording events stores them and get_events_for_mission returns them."""
    svc = TelemetryService()
    mission_id = "m1"
    svc.record(mission_id, TelemetryEventType.MISSION_RECEIVED, "api", {})
    svc.record(mission_id, TelemetryEventType.PATH_COMPUTED, "navigation", {"waypoints": 5})
    events = svc.get_events_for_mission(mission_id)
    assert len(events) == 2
    assert events[0].event_type == "mission_received"
    assert events[1].event_type == "path_computed"
    assert events[1].payload == {"waypoints": 5}


def test_telemetry_service_returns_events_in_chronological_order() -> None:
    """get_events_for_mission returns events sorted by timestamp."""
    svc = TelemetryService()
    mission_id = "m2"
    svc.record(mission_id, TelemetryEventType.PLAN_GENERATED, "planner", {})
    svc.record(mission_id, TelemetryEventType.MISSION_RECEIVED, "api", {})
    svc.record(mission_id, TelemetryEventType.PERCEPTION_COMPLETED, "perception", {})
    events = svc.get_events_for_mission(mission_id)
    assert len(events) == 3
    timestamps = [e.timestamp for e in events]
    assert timestamps == sorted(timestamps)


def test_mission_creation_emits_mission_received() -> None:
    """Creating a mission via API causes mission_received to be stored."""
    create_resp = client.post(
        "/missions",
        json={"mission_text": "Go to point A", "world_id": "w1"},
    )
    assert create_resp.status_code == 201
    mission_id = create_resp.json()["mission_id"]

    telemetry_resp = client.get(f"/missions/{mission_id}/telemetry")
    assert telemetry_resp.status_code == 200
    data = telemetry_resp.json()
    assert data["mission_id"] == mission_id
    assert data["count"] == 1
    assert len(data["events"]) == 1
    assert data["events"][0]["event_type"] == "mission_received"
    assert data["events"][0]["source_component"] == "api"
    assert data["events"][0]["payload"].get("mission_text") == "Go to point A"


def test_telemetry_unknown_mission_returns_404() -> None:
    """GET /missions/{id}/telemetry returns 404 when mission does not exist."""
    response = client.get("/missions/nonexistent_mission_id_xyz")
    assert response.status_code == 404
    assert response.json()["detail"] == "Mission not found"


def test_telemetry_response_shape() -> None:
    """GET telemetry returns mission_id, count, and events array."""
    create_resp = client.post(
        "/missions",
        json={"mission_text": "Shape check", "world_id": "w2"},
    )
    assert create_resp.status_code == 201
    mission_id = create_resp.json()["mission_id"]
    telemetry_resp = client.get(f"/missions/{mission_id}/telemetry")
    assert telemetry_resp.status_code == 200
    data = telemetry_resp.json()
    assert "mission_id" in data and data["mission_id"] == mission_id
    assert "count" in data and data["count"] == len(data["events"])
    assert "events" in data and isinstance(data["events"], list)


def test_telemetry_events_have_monotonic_sequence() -> None:
    """Returned events include sequence and are ordered by it."""
    svc = TelemetryService()
    mission_id = "m_seq"
    svc.record(mission_id, TelemetryEventType.MISSION_RECEIVED, "api", {})
    svc.record(mission_id, TelemetryEventType.PATH_COMPUTED, "navigation", {})
    events = svc.get_events_for_mission(mission_id)
    assert [e.sequence for e in events] == [1, 2]


def test_telemetry_cursor_reconnect():
    response = client.post("/missions", json={"mission_text": "Navigate to target"})
    mission_id = response.json()["mission_id"]
    first = client.get(f"/missions/{mission_id}/telemetry").json()
    cursor = first["events"][-1]["sequence"]
    assert client.get(f"/missions/{mission_id}/telemetry?after_sequence={cursor}").json()["events"] == []
    assert client.get(f"/missions/{mission_id}/telemetry?after_sequence=-1").status_code == 422


def test_durable_trace_export_survives_restart(tmp_path):
    from backend.storage.sqlite_journal import SQLiteJournal
    from backend.services.telemetry_service import TelemetryService
    path = str(tmp_path / "traces.sqlite3")
    first = TelemetryService(SQLiteJournal(path))
    first.record("mission-export", "test_event", "test", {"value": 42})
    second = TelemetryService(SQLiteJournal(path))
    trace = second.export()["mission-export"]
    assert len(trace) == 1
    assert trace[0]["sequence"] == 1
    assert trace[0]["payload"] == {"value": 42}


def test_sse_reconnect_cursor_and_terminal_event():
    from fastapi.testclient import TestClient
    from backend.api.main import app
    from backend.api.dependencies import get_telemetry_service
    client=TestClient(app)
    ident=client.post('/missions',json={'mission_text':'Go to target'}).json()['mission_id']
    telemetry=get_telemetry_service()
    telemetry.record(ident,'robot_state','test',{'robot_x':0,'robot_y':0,'simulation_time_seconds':0})
    last=telemetry.record(ident,'mission_completed','test',{})
    response=client.get('/missions/'+ident+'/stream',headers={'Last-Event-ID':str(last.sequence-1)})
    assert response.status_code==200
    assert response.headers['content-type'].startswith('text/event-stream')
    assert f'id: {last.sequence}\n' in response.text
    assert 'event: terminal' in response.text
    assert 'robot_state' not in response.text
    assert client.get('/missions/'+ident+'/stream',headers={'Last-Event-ID':'invalid'}).status_code==422


def test_sse_rerun_does_not_close_on_previous_terminal_event(monkeypatch):
    from threading import Thread,Event
    from fastapi.testclient import TestClient
    from backend.api.main import app
    from backend.api.dependencies import get_telemetry_service
    client=TestClient(app)
    ident=client.post('/missions',json={'mission_text':'Go to target'}).json()['mission_id']
    telemetry=get_telemetry_service();old=telemetry.record(ident,'mission_completed','test',{})
    read=Event();original=telemetry.get_events_for_mission
    def snapshot(mission):
        result=original(mission);read.set();return result
    monkeypatch.setattr(telemetry,'get_events_for_mission',snapshot)
    def new_run():
        assert read.wait(5)
        telemetry.record(ident,'robot_state','test',{'robot_x':1,'robot_y':2})
        telemetry.record(ident,'mission_completed','test',{})
    thread=Thread(target=new_run);thread.start()
    response=client.get('/missions/'+ident+'/stream',params={'after_sequence':old.sequence,'await_new_run':'true'})
    thread.join(5)
    assert response.status_code==200 and 'robot_state' in response.text
    assert f'id: {old.sequence}\n' not in response.text
