"""Camera configuration and captured frame schemas."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class CameraConfig(BaseModel):
    """Camera/view parameters for simulator frame capture."""

    width: int = Field(..., gt=0, le=4096)
    height: int = Field(..., gt=0, le=4096)
    target_x: float = 0.0
    target_y: float = 0.0
    target_z: float = 0.0
    distance: float = Field(..., gt=0)
    yaw: float = 0.0
    pitch: float = -60.0
    roll: float = 0.0
    fov_degrees: float = Field(60.0, gt=0, lt=180)
    near: float = Field(0.1, gt=0)
    far: float = Field(500.0, gt=0)


class CapturedFrame(BaseModel):
    """Single RGB frame from the simulator camera."""

    width: int = Field(..., gt=0)
    height: int = Field(..., gt=0)
    rgb: Any = Field(..., description="RGB image as (H, W, 3) uint8 numpy array")
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)
