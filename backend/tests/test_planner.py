"""Planner backends and PlannerService tests."""

import os
from unittest.mock import patch

import httpx

from backend.schemas.planner import MissionPlanRequest
from backend.services.planner_backends.llm_planner import try_plan_with_llm
from backend.services.planner_backends.rule_based_planner import plan_from_rules
from backend.services.planner_service import PlannerService


def test_rule_based_red_and_avoid() -> None:
    p = plan_from_rules("Go to the red cube and avoid obstacles")
    assert p.planner_mode == "rule_based"
    assert p.target_label == "red cube"
    assert "avoid_obstacles" in p.constraints
    assert "Select target: target" in p.plan_steps
    assert "Navigate with obstacle avoidance" in p.plan_steps


def test_rule_based_default_navigate() -> None:
    p = plan_from_rules("Reach the goal")
    assert p.goal_type == "navigate_to_target"
    assert p.target_label == "target"
    assert p.constraints == []
    assert "Navigate to target" in p.plan_steps


def test_planner_service_no_api_key_uses_rule() -> None:
    with patch.dict(
        os.environ,
        {"OPENAI_API_KEY": "", "AUTONOMY_PLANNER_MODE": "auto"},
        clear=False,
    ):
        svc = PlannerService(api_key="")
        r = svc.plan(MissionPlanRequest(mission_text="red target"))
    assert r.plan.planner_mode == "rule_based"
    assert r.plan.target_label == "red cube"


def test_planner_service_force_rule_based() -> None:
    with patch.dict(
        os.environ,
        {"OPENAI_API_KEY": "sk-test", "AUTONOMY_PLANNER_MODE": "rule_based"},
        clear=False,
    ):
        svc = PlannerService(api_key="sk-test")
        r = svc.plan(MissionPlanRequest(mission_text="anything"))
    assert r.plan.planner_mode == "rule_based"


def test_malformed_llm_response_falls_back_to_rule() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "plain text no json"}}]},
        )

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    with patch.dict(os.environ, {"AUTONOMY_PLANNER_MODE": "llm"}, clear=False):
        svc = PlannerService(api_key="sk-fake", model="gpt-4o-mini", http_client=client)
        r = svc.plan(MissionPlanRequest(mission_text="Visit red cube"))
    assert r.plan.planner_mode == "rule_based"
    client.close()


def test_try_plan_with_llm_valid_json() -> None:
    payload = {
        "goal_type": "navigate_to_target",
        "target_label": "red cube",
        "constraints": [],
        "plan_steps": ["Select target: target", "Navigate to target"],
        "confidence": 0.9,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(payload)}}]},
        )

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    plan = try_plan_with_llm("mission", "sk-x", "gpt-4o-mini", client=client)
    client.close()
    assert plan is not None
    assert plan.planner_mode == "llm"
    assert plan.plan_steps == payload["plan_steps"]


def test_try_plan_with_llm_http_error_returns_none() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "server"})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    plan = try_plan_with_llm("m", "sk-x", "gpt-4o-mini", client=client)
    client.close()
    assert plan is None
