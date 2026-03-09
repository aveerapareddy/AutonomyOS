"""Scenario configuration for generated worlds."""

from typing import List, Tuple

from pydantic import BaseModel, Field


class ScenarioConfig(BaseModel):
    """Describes a single generated world for benchmarking."""

    scenario_id: str
    scenario_name: str = ""
    world_bounds: Tuple[float, float, float, float]
    obstacle_positions: List[Tuple[float, float]] = Field(default_factory=list)
    obstacle_types: List[str] = Field(default_factory=list)
    target_position: Tuple[float, float]
    robot_start_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
