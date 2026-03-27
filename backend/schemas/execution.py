"""Mission execution summary and plan schemas."""

from typing import Any, Optional

from pydantic import BaseModel, Field


class SceneObstacle(BaseModel):
    """World-space obstacle center for operator visualization (matches planning layout)."""

    x: float
    y: float


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
    planner_mode: Optional[str] = None
    goal_type: Optional[str] = None
    target_label: Optional[str] = None
    constraints: list[str] = Field(default_factory=list)
    detected_target: Optional[dict[str, Any]] = None
    world_bounds: Optional[tuple[float, float, float, float]] = None
    obstacles: list[SceneObstacle] = Field(default_factory=list)
    path_found: bool = False
    waypoint_count: int = 0
    path_length_raw: Optional[int] = None
    path_length_simplified: Optional[int] = None
    grid_inflation_cells: Optional[int] = None
    telemetry_count: int = 0
    message: Optional[str] = None
    execution_steps: list[ExecutionStep] = Field(default_factory=list)
    final_robot_position: Optional[dict[str, float]] = None
    execution_status: Optional[str] = None
