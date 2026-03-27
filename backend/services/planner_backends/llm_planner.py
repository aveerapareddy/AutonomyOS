"""OpenAI-compatible chat completion for structured MissionPlan JSON."""

import json
import os
from typing import Any, Optional

import httpx

from backend.schemas.planner import MissionPlan
from backend.services.planner_backends.rule_based_planner import plan_from_rules

DEFAULT_MODEL = "gpt-4o-mini"
OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"

_SYSTEM = """You are a warehouse robot mission planner. Convert the user's mission into a short JSON object only.
Keys (all required): goal_type (string, e.g. navigate_to_target), target_label (string or null), constraints (array of strings), plan_steps (array of short imperative strings), confidence (number 0-1 or null).
Use constraints like "avoid_obstacles" only if the mission asks to avoid obstacles.
plan_steps must be non-empty and executable at a high level (e.g. "Select target: target", "Navigate to target").
Output raw JSON only, no markdown."""


def _extract_json_object(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("{") or "\n{" in part:
                idx = part.find("{")
                if idx >= 0:
                    text = part[idx:]
                break
    start = text.find("{")
    if start < 0:
        return None
    try:
        data, _ = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _draft_to_mission_plan(data: dict[str, Any]) -> MissionPlan | None:
    steps = data.get("plan_steps")
    if not isinstance(steps, list) or not all(isinstance(s, str) for s in steps):
        return None
    if len(steps) == 0:
        return None
    gt = data.get("goal_type")
    if not isinstance(gt, str) or not gt.strip():
        gt = "navigate_to_target"
    tl = data.get("target_label")
    if tl is not None and not isinstance(tl, str):
        tl = None
    cons = data.get("constraints")
    if not isinstance(cons, list):
        cons = []
    cons_out: list[str] = []
    for c in cons:
        if isinstance(c, str) and c.strip():
            cons_out.append(c.strip())
    conf = data.get("confidence")
    if conf is not None:
        try:
            conf = float(conf)
            if conf < 0.0 or conf > 1.0:
                conf = None
        except (TypeError, ValueError):
            conf = None
    return MissionPlan(
        goal_type=gt.strip(),
        target_label=tl.strip() if isinstance(tl, str) and tl.strip() else None,
        constraints=cons_out,
        plan_steps=steps,
        confidence=conf,
        planner_mode="llm",
    )


def try_plan_with_llm(
    mission_text: str,
    api_key: str,
    model: str,
    client: Optional[httpx.Client] = None,
    timeout_s: float = 60.0,
) -> MissionPlan | None:
    if not api_key.strip():
        return None
    owns_client = client is None
    if client is None:
        client = httpx.Client(timeout=timeout_s)
    try:
        body: dict[str, Any] = {
            "model": model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": mission_text},
            ],
            "response_format": {"type": "json_object"},
        }
        r = client.post(
            OPENAI_CHAT_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=body,
        )
        if r.status_code != 200:
            return None
        payload = r.json()
        choices = payload.get("choices")
        if not choices:
            return None
        content = choices[0].get("message", {}).get("content")
        if not isinstance(content, str):
            return None
        data = _extract_json_object(content)
        if data is None:
            return None
        plan = _draft_to_mission_plan(data)
        return plan
    except (httpx.HTTPError, TypeError, KeyError, json.JSONDecodeError):
        return None
    finally:
        if owns_client:
            client.close()


def plan_with_llm_or_fallback(
    mission_text: str,
    api_key: str | None,
    model: str | None,
    client: Optional[httpx.Client] = None,
) -> MissionPlan:
    key = (api_key or os.environ.get("OPENAI_API_KEY") or "").strip()
    mdl = (model or os.environ.get("OPENAI_MODEL") or DEFAULT_MODEL).strip()
    if not key:
        return plan_from_rules(mission_text)
    out = try_plan_with_llm(mission_text, key, mdl, client=client)
    if out is None:
        return plan_from_rules(mission_text)
    return out
