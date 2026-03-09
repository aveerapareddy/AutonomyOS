"""Benchmark run request and result schemas."""

from typing import Optional, Tuple

from pydantic import BaseModel, Field


class BenchmarkRunRequest(BaseModel):
    """Input for starting a benchmark run."""

    benchmark_name: str = Field(..., min_length=1)
    scenario_count: int = Field(..., ge=1, le=100)
    seed: Optional[int] = None


class ScenarioBenchmarkResult(BaseModel):
    """Result of running one scenario in a benchmark."""

    scenario_id: str
    scenario_name: str = ""
    robot_start_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    target_position: Tuple[float, float] = (0.0, 0.0)
    success: bool
    path_found: bool
    waypoint_count: int = 0
    path_length_raw: Optional[int] = None
    execution_steps: int = 0
    message: Optional[str] = None


class BenchmarkSummary(BaseModel):
    """Aggregate result of a benchmark run."""

    benchmark_id: str
    benchmark_name: str
    total_scenarios: int
    success_count: int
    failure_count: int
    success_rate: float
    average_waypoint_count: float
    average_execution_steps: float
    scenario_results: list[ScenarioBenchmarkResult] = Field(default_factory=list)
