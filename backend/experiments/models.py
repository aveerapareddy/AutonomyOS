"""Bounded inputs and explicit evaluation outputs."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class ExperimentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(default="warehouse-reference", min_length=1, max_length=100)
    seed: int = Field(default=42, ge=0, le=2**31-1)
    scenario_count: int = Field(default=5, ge=1, le=100)
    minimum_success_rate: float = Field(default=0.8, ge=0, le=1, allow_inf_nan=False)


class ExperimentReport(BaseModel):
    schema_version: str = "2.0"
    run_id: str
    status: Literal["completed", "failed"]
    request: ExperimentRequest
    scenario_hash: str
    outcome_hash: str
    evaluation_passed: bool
    summary: dict
    provenance: dict
    limitations: list[str]
