"""Orchestrator and execute endpoint tests."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.schemas.perception import PerceptionResult
from backend.schemas.world import WorldObject
from backend.services.mission_service import MissionService
from backend.services.orchestrator_service import OrchestratorService
from backend.services.telemetry_service import TelemetryService
from backend.storage.repositories.mission_repository import InMemoryMissionRepository

client = TestClient(app)


def test_execute_mission_not_found() -> None:
    """POST /missions/{id}/execute returns 404 when mission does not exist."""
    response = client.post("/missions/nonexistent_id_xyz/execute")
    assert response.status_code == 404
    assert response.json()["detail"] == "Mission not found"


def test_execute_mission_success() -> None:
    """Successful orchestration including waypoint execution returns summary with execution result."""
    pytest.importorskip("pybullet")
    create_resp = client.post(
        "/missions",
        json={"mission_text": "Go to the red cube", "world_id": "w1"},
    )
    assert create_resp.status_code == 201
    mission_id = create_resp.json()["mission_id"]

    exec_resp = client.post(f"/missions/{mission_id}/execute")
    assert exec_resp.status_code == 200
    data = exec_resp.json()
    assert data["mission_id"] == mission_id
    assert data["status"] == "completed"
    assert isinstance(data["plan_steps"], list)
    assert data["detected_target"] is not None
    assert data["path_found"] is True
    assert data["waypoint_count"] >= 1
    assert data["telemetry_count"] >= 1
    assert data["execution_status"] == "completed"
    assert data["final_robot_position"] is not None
    assert isinstance(data["execution_steps"], list)
    assert len(data["execution_steps"]) == data["waypoint_count"]

    telemetry_resp = client.get(f"/missions/{mission_id}/telemetry")
    assert telemetry_resp.status_code == 200
    events = telemetry_resp.json()["events"]
    event_types = [e["event_type"] for e in events]
    assert "mission_received" in event_types
    assert "plan_generated" in event_types
    assert "perception_completed" in event_types
    assert "path_computed" in event_types
    assert "execution_started" in event_types
    assert "waypoint_reached" in event_types
    assert "execution_completed" in event_types
    assert "mission_completed" in event_types
    assert data["telemetry_count"] == len(events)


def test_execute_no_target_found() -> None:
    """When perception returns no target, orchestration fails with useful summary."""
    from backend.schemas.mission import MissionRequest

    mission_repo = InMemoryMissionRepository()
    mission_svc = MissionService(repository=mission_repo)
    telemetry_svc = TelemetryService()
    resp = mission_svc.create(MissionRequest(mission_text="Find the thing"))
    mission_id = resp.mission_id

    with patch("backend.services.orchestrator_service.perceive_from_objects") as mock_perceive:
        mock_perceive.return_value = PerceptionResult(detected_targets=[], detected_obstacles=[])
        orch = OrchestratorService(mission_service=mission_svc, telemetry_service=telemetry_svc)
        summary = orch.execute(mission_id)
    assert summary is not None
    assert summary.status == "failed"
    assert summary.path_found is False
    assert summary.message == "No target found"


def test_execute_no_path_found() -> None:
    """When path is blocked, orchestration fails with useful summary."""
    from backend.schemas.mission import MissionRequest

    mission_repo = InMemoryMissionRepository()
    mission_svc = MissionService(repository=mission_repo)
    telemetry_svc = TelemetryService()
    resp = mission_svc.create(MissionRequest(mission_text="Navigate"))
    mission_id = resp.mission_id

    def layout_blocked_goal() -> tuple:
        bounds = (-10.0, 10.0, -10.0, 10.0)
        target_xy = (1.0, 1.0)
        obstacles = [
            WorldObject(object_id="o0", object_type="wall", x=-3.0, y=0.0),
            WorldObject(object_id="o1", object_type="wall", x=3.0, y=0.0),
            WorldObject(object_id="o2", object_type="block", x=target_xy[0], y=target_xy[1]),
        ]
        target = WorldObject(object_id="target", object_type="target", x=target_xy[0], y=target_xy[1])
        return bounds, obstacles, target

    orch = OrchestratorService(
        mission_service=mission_svc,
        telemetry_service=telemetry_svc,
        world_layout_provider=layout_blocked_goal,
    )
    summary = orch.execute(mission_id)
    assert summary is not None
    assert summary.status == "failed"
    assert summary.path_found is False
    assert summary.detected_target is not None
