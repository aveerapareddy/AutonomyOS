"""Camera configuration and captured frame schemas."""

from typing import Any

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


class CameraPose(BaseModel):
    """World-space camera pose at capture time (degrees for angles)."""

    position_x: float
    position_y: float
    position_z: float
    yaw: float
    pitch: float
    roll: float


class CameraIntrinsics(BaseModel):
    """Render intrinsics aligned with PyBullet projection (FOV in degrees)."""

    width: int = Field(..., gt=0)
    height: int = Field(..., gt=0)
    fov: float = Field(..., gt=0, lt=180)
    near_plane: float = Field(..., gt=0)
    far_plane: float = Field(..., gt=0)


class CapturedFrame(BaseModel):
    """RGB frame with pose and intrinsics for downstream projection."""

    rgb: Any = Field(..., description="RGB image as (H, W, 3) uint8 numpy array")
    width: int = Field(..., gt=0)
    height: int = Field(..., gt=0)
    camera_pose: CameraPose
    camera_intrinsics: CameraIntrinsics
    timestamp: float

    model_config = ConfigDict(arbitrary_types_allowed=True)
