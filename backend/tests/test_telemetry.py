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
