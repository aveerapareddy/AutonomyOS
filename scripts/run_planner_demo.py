"""Run mission planner on sample texts; print MissionPlan and downstream mapping hints."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import os

from backend.schemas.perception import DetectedObject
from backend.schemas.planner import MissionPlanRequest
from backend.services.navigation_constraints import grid_inflation_cells
from backend.services.planner_service import PlannerService
from backend.services.target_selection import select_navigation_goal


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
    fake_targets = [
        DetectedObject(object_id="target", object_type="target", x=5.0, y=3.0, confidence=1.0),
    ]
    fake_obstacles = [
        DetectedObject(object_id="obstacle_2", object_type="block", x=1.0, y=1.0, confidence=1.0),
    ]
    for text in samples:
        r = svc.plan(MissionPlanRequest(mission_text=text))
        p = r.plan
        inflation = grid_inflation_cells(list(p.constraints))
        sel, err = select_navigation_goal(fake_targets, fake_obstacles, p.target_label)
        print(f"\nMission: {text!r}")
        print(f"  planner_mode: {p.planner_mode}")
        print(f"  goal_type: {p.goal_type}")
        print(f"  target_label: {p.target_label}")
        print(f"  constraints: {p.constraints}")
        print(f"  confidence: {p.confidence}")
        print(f"  plan_steps: {p.plan_steps}")
        print(f"  downstream: grid_inflation_cells={inflation} | selected={getattr(sel, 'object_id', None)} err={err}")


if __name__ == "__main__":
    main()
