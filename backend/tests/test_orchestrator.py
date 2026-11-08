"""Orchestrator and execute endpoint tests."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.schemas.execution import ExecutionResult
from backend.schemas.navigation import NavigationResult, Waypoint
from backend.schemas.perception import PerceptionResult
from backend.schemas.planner import MissionPlan, MissionPlanRequest, MissionPlanResponse
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
    assert data.get("planner_mode") in ("rule_based", "llm")
    assert data.get("goal_type") is not None
    assert data.get("path_length_simplified") == data["waypoint_count"]
    assert data.get("grid_inflation_cells") == 1
    assert data.get("world_bounds") == [-10.0, 10.0, -10.0, 10.0]
    obstacles = data.get("obstacles") or []
    assert len(obstacles) == 3
    obstacle_xy = {(round(o["x"], 5), round(o["y"], 5)) for o in obstacles}
    assert (-3.0, 0.0) in obstacle_xy
    assert (3.0, 0.0) in obstacle_xy
    assert (1.0, 1.0) in obstacle_xy

    telemetry_resp = client.get(f"/missions/{mission_id}/telemetry")
    assert telemetry_resp.status_code == 200
    events = telemetry_resp.json()["events"]
    event_types = [e["event_type"] for e in events]
    assert "mission_received" in event_types
    assert "plan_generated" in event_types
    plan_events = [e for e in events if e["event_type"] == "plan_generated"]
    assert len(plan_events) >= 1
    pg = plan_events[0]["payload"]
    assert pg.get("planner_mode") in ("rule_based", "llm")
    assert "goal_type" in pg
    assert "plan_steps" in pg
    assert isinstance(pg.get("constraints"), list)
    assert pg.get("grid_inflation_cells") is not None
    path_ev = next(e for e in events if e["event_type"] == "path_computed")
    assert path_ev["payload"].get("path_length_raw") is not None
    assert path_ev["payload"].get("grid_inflation_cells") is not None
    assert "perception_completed" in event_types
    assert "path_computed" in event_types
    assert "execution_started" in event_types
    assert "waypoint_reached" in event_types
    assert "execution_completed" in event_types
    assert "mission_completed" in event_types
    assert data["telemetry_count"] == len(events)


def test_orchestrator_calls_planner_with_mission_text() -> None:
    from backend.schemas.mission import MissionRequest

    mission_repo = InMemoryMissionRepository()
    mission_svc = MissionService(repository=mission_repo)
    telemetry_svc = TelemetryService()
    resp = mission_svc.create(MissionRequest(mission_text="Custom mission phrase"))
    mission_id = resp.mission_id
    custom_steps = ["step_a", "step_b"]
    mock_planner = MagicMock()
    mock_planner.plan.return_value = MissionPlanResponse(
        plan=MissionPlan(
            goal_type="inspect",
            target_label="dock",
            constraints=["slow"],
            plan_steps=custom_steps,
            confidence=0.5,
            planner_mode="llm",
        )
    )
    with patch("backend.services.orchestrator_service.perceive_from_objects") as mock_perceive:
        mock_perceive.return_value = PerceptionResult(detected_targets=[], detected_obstacles=[])
        orch = OrchestratorService(
            mission_service=mission_svc,
            telemetry_service=telemetry_svc,
            planner_service=mock_planner,
        )
        summary = orch.execute(mission_id)
    mock_planner.plan.assert_called_once()
    req = mock_planner.plan.call_args[0][0]
    assert isinstance(req, MissionPlanRequest)
    assert req.mission_text == "Custom mission phrase"
    assert summary is not None
    assert summary.plan_steps == custom_steps
    events = telemetry_svc.get_events_for_mission(mission_id)
    plan_ev = next(e for e in events if e.event_type == "plan_generated")
    assert plan_ev.payload.get("planner_mode") == "llm"
    assert plan_ev.payload.get("plan_steps") == custom_steps
    assert summary.planner_mode == "llm"
    assert summary.goal_type == "inspect"


def test_execute_avoid_obstacles_raises_grid_inflation() -> None:
    pytest.importorskip("pybullet")
    create_resp = client.post(
        "/missions",
        json={
            "mission_text": "Go to the red cube avoiding obstacles",
            "world_id": "w1",
        },
    )
    assert create_resp.status_code == 201
    mission_id = create_resp.json()["mission_id"]
    exec_resp = client.post(f"/missions/{mission_id}/execute")
    assert exec_resp.status_code == 200
    assert exec_resp.json().get("grid_inflation_cells") == 2


def test_execute_unsupported_planned_target_fails() -> None:
    from backend.schemas.mission import MissionRequest

    mission_repo = InMemoryMissionRepository()
    mission_svc = MissionService(repository=mission_repo)
    telemetry_svc = TelemetryService()
    resp = mission_svc.create(MissionRequest(mission_text="x"))
    mission_id = resp.mission_id
    mock_planner = MagicMock()
    mock_planner.plan.return_value = MissionPlanResponse(
        plan=MissionPlan(
            goal_type="navigate_to_target",
            target_label="unknown_sku_label",
            constraints=[],
            plan_steps=["Select target: target", "Navigate to target"],
            confidence=1.0,
            planner_mode="rule_based",
        )
    )
    orch = OrchestratorService(
        mission_service=mission_svc,
        telemetry_service=telemetry_svc,
        planner_service=mock_planner,
    )
    summary = orch.execute(mission_id)
    assert summary is not None
    assert summary.status == "failed"
    assert summary.path_found is False
    assert "no_detection_matches" in (summary.message or "")


def test_planner_driven_block_goal() -> None:
    from backend.schemas.mission import MissionRequest

    mission_repo = InMemoryMissionRepository()
    mission_svc = MissionService(repository=mission_repo)
    telemetry_svc = TelemetryService()
    resp = mission_svc.create(MissionRequest(mission_text="Go to the block"))
    mission_id = resp.mission_id
    mock_planner = MagicMock()
    mock_planner.plan.return_value = MissionPlanResponse(
        plan=MissionPlan(
            goal_type="navigate_to_target",
            target_label="block",
            constraints=[],
            plan_steps=["Select target: block", "Navigate to target"],
            confidence=1.0,
            planner_mode="llm",
        )
    )
    nav = NavigationResult(
        path_found=True,
        waypoints=[Waypoint(x=0.0, y=0.0), Waypoint(x=1.0, y=1.0)],
        path_length=2,
        path_length_raw=5,
    )
    done = ExecutionResult(
        execution_status="completed",
        execution_steps=[],
        final_robot_position={"x": 1.0, "y": 1.0, "theta": 0.0},
    )
    with patch("backend.services.orchestrator_service.plan_path", return_value=nav):
        with patch("backend.services.orchestrator_service.run_sim_execution", return_value=done):
            orch = OrchestratorService(
                mission_service=mission_svc,
                telemetry_service=telemetry_svc,
                planner_service=mock_planner,
            )
            summary = orch.execute(mission_id)
    assert summary is not None
    assert summary.detected_target is not None
    assert summary.detected_target.get("object_type") == "block"
    assert summary.path_found is True
    assert summary.path_length_raw == 5
    assert summary.path_length_simplified == 2


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
