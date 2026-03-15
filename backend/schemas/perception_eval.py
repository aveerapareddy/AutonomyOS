"""Perception evaluation: truth vs predicted object matching."""

from typing import Optional

from pydantic import BaseModel, Field


class PerceptionMatch(BaseModel):
    truth_object_id: Optional[str] = None
    predicted_object_id: Optional[str] = None
    truth_type: Optional[str] = None
    predicted_type: Optional[str] = None
    matched: bool = False
    confidence: Optional[float] = None


class PerceptionEvalResult(BaseModel):
    backend_name: str = ""
    truth_count: int = 0
    predicted_count: int = 0
    matched_count: int = 0
    unmatched_truth_count: int = 0
    unmatched_prediction_count: int = 0
    object_matches: list[PerceptionMatch] = Field(default_factory=list)
    message: Optional[str] = None
