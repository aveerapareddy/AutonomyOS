"""Replay service and API tests."""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.schemas.telemetry import TelemetryEvent
from backend.services.replay_service import ReplayService
from backend.services.telemetry_service import TelemetryService

client = TestClient(app)


def test_replay_built_from_telemetry() -> None:
    """Replay frames are derived from telemetry events in order."""
    telemetry = TelemetryService()
    replay_svc = ReplayService(telemetry)
    mission_id = "m1"
    telemetry.record(mission_id, "plan_generated", "planner", {"plan_steps": ["a", "b"]})
    telemetry.record(mission_id, "execution_started", "execution_engine", {"robot_x": 0.0, "robot_y": 0.0})
    replay = replay_svc.build_replay(mission_id)
    assert replay.mission_id == mission_id
    assert replay.frame_count == 2
    assert len(replay.frames) == 2
    assert replay.frames[0].event_type == "plan_generated"
    assert replay.frames[1].event_type == "execution_started"
    assert replay.frames[1].robot_position == {"x": 0.0, "y": 0.0}


def test_replay_frame_ordering_stable() -> None:
    """Frames follow telemetry sequence order."""
    telemetry = TelemetryService()
    replay_svc = ReplayService(telemetry)
    mission_id = "m2"
    for i in range(3):
        telemetry.record(mission_id, f"event_{i}", "test", {})
    replay = replay_svc.build_replay(mission_id)
    assert replay.frame_count == 3
    for i, frame in enumerate(replay.frames):
        assert frame.index == i
    assert [f.event_type for f in replay.frames] == ["event_0", "event_1", "event_2"]


def test_replay_unknown_mission_returns_404() -> None:
    """GET /missions/{id}/replay returns 404 when mission does not exist."""
    response = client.get("/missions/nonexistent_mission_xyz/replay")
    assert response.status_code == 404
    assert response.json()["detail"] == "Mission not found"


def test_replay_execution_telemetry_has_robot_position() -> None:
    """Execution events with robot_x/robot_y produce frames with robot_position."""
    telemetry = TelemetryService()
    replay_svc = ReplayService(telemetry)
    mission_id = "m3"
    telemetry.record(
        mission_id,
        "waypoint_reached",
        "execution_engine",
        {"waypoint_index": 1, "target_x": 1.0, "target_y": 0.5, "robot_x": 0.99, "robot_y": 0.48},
    )
    replay = replay_svc.build_replay(mission_id)
    assert replay.frame_count == 1
    frame = replay.frames[0]
    assert frame.robot_position == {"x": 0.99, "y": 0.48}
    assert frame.target_position == {"x": 1.0, "y": 0.5}
    assert frame.event_type == "waypoint_reached"


def test_replay_empty_telemetry_returns_empty_frames() -> None:
    """Replay for mission with no telemetry returns empty frame list."""
    telemetry = TelemetryService()
    replay_svc = ReplayService(telemetry)
    replay = replay_svc.build_replay("mission_no_events")
    assert replay.mission_id == "mission_no_events"
    assert replay.frame_count == 0
    assert replay.frames == []


def test_replay_api_returns_replay_for_existing_mission() -> None:
    """GET /missions/{id}/replay returns 200 with replay when mission exists."""
    create_resp = client.post(
        "/missions",
        json={"mission_text": "Go to target", "world_id": "w1"},
    )
    assert create_resp.status_code == 201
    mission_id = create_resp.json()["mission_id"]
    replay_resp = client.get(f"/missions/{mission_id}/replay")
    assert replay_resp.status_code == 200
    data = replay_resp.json()
    assert data["mission_id"] == mission_id
    assert data["frame_count"] >= 1
    assert len(data["frames"]) == data["frame_count"]
    assert data["frames"][0]["event_type"] == "mission_received"


def test_event_to_frame_normalizes_payload() -> None:
    """event_to_frame extracts robot_position and target_position; payload preserved."""
    from backend.services.replay_service import event_to_frame

    event = TelemetryEvent(
        event_id="e1",
        mission_id="m",
        sequence=1,
        timestamp=datetime.now(timezone.utc),
        event_type="execution_completed",
        source_component="execution_engine",
        payload={"robot_x": 5.0, "robot_y": 3.0, "robot_theta": 0.1, "waypoints_reached": 3},
    )
    frame = event_to_frame(event, 0)
    assert frame.index == 0
    assert frame.event_type == "execution_completed"
    assert frame.robot_position == {"x": 5.0, "y": 3.0, "theta": 0.1}
    assert frame.target_position is None
    assert frame.payload["waypoints_reached"] == 3
