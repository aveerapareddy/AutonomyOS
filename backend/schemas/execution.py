"""Mission execution summary and plan schemas."""

from typing import Any, Optional

from pydantic import BaseModel, Field


class ExecutionStep(BaseModel):
    """Single step in waypoint execution (e.g. waypoint index, reached)."""

    waypoint_index: int
    target_x: float
    target_y: float
    reached: bool


class ExecutionResult(BaseModel):
    """Result of running WaypointExecutor. execution_status: \"completed\" | \"failed\"."""

    execution_status: str
    execution_steps: list[ExecutionStep] = Field(default_factory=list)
    final_robot_position: Optional[dict[str, float]] = None
    message: Optional[str] = None


class MissionExecutionSummary(BaseModel):
    """Result of running the orchestration pipeline for a mission. status: \"completed\" | \"failed\" (lowercase, stable)."""

    mission_id: str
    status: str
    plan_steps: list[str] = Field(default_factory=list)
    detected_target: Optional[dict[str, Any]] = None
    path_found: bool = False
    waypoint_count: int = 0
    path_length_raw: Optional[int] = None
    telemetry_count: int = 0
    message: Optional[str] = None
    execution_steps: list[ExecutionStep] = Field(default_factory=list)
    final_robot_position: Optional[dict[str, float]] = None
    execution_status: Optional[str] = None
