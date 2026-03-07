"""Perception request and result schemas."""

from typing import Union

from pydantic import BaseModel, Field


class DetectedObject(BaseModel):
    object_id: Union[str, int]
    object_type: str
    x: float
    y: float
    confidence: float = Field(..., ge=0.0, le=1.0)


class PerceptionRequest(BaseModel):
    include_obstacles: bool = True
    include_targets: bool = True


class PerceptionResult(BaseModel):
    detected_targets: list[DetectedObject] = Field(default_factory=list)
    detected_obstacles: list[DetectedObject] = Field(default_factory=list)
    message: str | None = None
