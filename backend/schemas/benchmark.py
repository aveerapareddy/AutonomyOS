"""Benchmark run request and response schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class BenchmarkRunRequest(BaseModel):
    """Input for starting a benchmark run."""

    benchmark_name: str = Field(..., min_length=1)
    scenario_count: int = Field(..., ge=1)


class BenchmarkRunResponse(BaseModel):
    """Benchmark run creation or status response."""

    benchmark_id: str
    status: str
    created_at: datetime
