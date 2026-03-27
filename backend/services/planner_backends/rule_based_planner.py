"""Deterministic mission planning from keywords."""

from backend.schemas.planner import MissionPlan


def plan_from_rules(mission_text: str) -> MissionPlan:
    text_lower = mission_text.lower().strip()
    constraints: list[str] = []
    if "avoid" in text_lower:
        constraints.append("avoid_obstacles")

    target_label: str | None
    if "red" in text_lower:
        target_label = "red cube"
    else:
        target_label = "target"

    plan_steps: list[str] = []
    if "red" in text_lower or "target" in text_lower or not text_lower:
        plan_steps.append("Select target: target")
    else:
        plan_steps.append("Select target: target")
    if "avoid" in text_lower:
        plan_steps.append("Navigate with obstacle avoidance")
    else:
        plan_steps.append("Navigate to target")

    return MissionPlan(
        goal_type="navigate_to_target",
        target_label=target_label,
        constraints=constraints,
        plan_steps=plan_steps,
        confidence=1.0,
        planner_mode="rule_based",
    )
