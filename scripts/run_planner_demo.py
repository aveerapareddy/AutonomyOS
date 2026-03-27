"""Run mission planner on sample texts; prints MissionPlan and planner_mode."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import os

from backend.schemas.planner import MissionPlanRequest
from backend.services.planner_service import PlannerService


def main() -> None:
    samples = [
        "Go to the red cube",
        "Navigate to the target avoiding obstacles",
        "Inspect the loading dock area",
    ]
    svc = PlannerService()
    has_key = bool((os.environ.get("OPENAI_API_KEY") or "").strip())
    mode = (os.environ.get("AUTONOMY_PLANNER_MODE") or "auto").lower()
    print(f"OPENAI_API_KEY set: {has_key} | AUTONOMY_PLANNER_MODE={mode}")
    for text in samples:
        r = svc.plan(MissionPlanRequest(mission_text=text))
        p = r.plan
        print(f"\nMission: {text!r}")
        print(f"  planner_mode: {p.planner_mode}")
        print(f"  goal_type: {p.goal_type}")
        print(f"  target_label: {p.target_label}")
        print(f"  constraints: {p.constraints}")
        print(f"  confidence: {p.confidence}")
        print(f"  plan_steps: {p.plan_steps}")


if __name__ == "__main__":
    main()
