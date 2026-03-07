"""Navigation request and result schemas."""

from pydantic import BaseModel, Field


class Waypoint(BaseModel):
    x: float
    y: float


class NavigationRequest(BaseModel):
    start_x: float
    start_y: float
    goal_x: float
    goal_y: float


class NavigationResult(BaseModel):
    path_found: bool
    waypoints: list[Waypoint] = Field(default_factory=list)
    path_length: int = 0
    message: str | None = None
