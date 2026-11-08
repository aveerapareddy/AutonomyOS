"""Mission planning request/response schemas."""

from typing import Optional

from pydantic import BaseModel, Field


class MissionPlan(BaseModel):
    goal_type: str
    target_label: Optional[str] = None
    constraints: list[str] = Field(default_factory=list)
    plan_steps: list[str] = Field(default_factory=list)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    planner_mode: str


class MissionPlanRequest(BaseModel):
    mission_text: str


class MissionPlanResponse(BaseModel):
    plan: MissionPlan
