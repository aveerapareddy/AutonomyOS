"""Schemas for approximate image-to-world projection."""

from pydantic import BaseModel, Field

from backend.schemas.perception import DetectedObject


class ProjectionInput(BaseModel):
    """Normalized image point and optional depth hint."""

    image_x: float = Field(..., ge=0.0, le=1.0)
    image_y: float = Field(..., ge=0.0, le=1.0)
    depth: float = Field(1.0, gt=0.0)


class ProjectionOutput(BaseModel):
    """Approximate projected world coordinates."""

    world_x: float
    world_y: float
    world_z: float | None = None
    valid: bool
    message: str | None = None


class ProjectedDetection(BaseModel):
    """Detected object with projected world output."""

    original: DetectedObject
    projection: ProjectionOutput
