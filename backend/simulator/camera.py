"""Simulator camera and frame capture. Uses PyBullet getCameraImage."""

import time
from typing import Optional

import numpy as np

try:
    import pybullet as pb
except ImportError:
    pb = None

from backend.schemas.camera import (
    CameraConfig,
    CameraIntrinsics,
    CameraPose,
    CapturedFrame,
)

DEFAULT_WIDTH = 640
DEFAULT_HEIGHT = 480
DEFAULT_DISTANCE = 25.0
DEFAULT_PITCH = -60.0
UP_AXIS_Z = 2


def default_camera_config(
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    target_x: float = 0.0,
    target_y: float = 0.0,
    target_z: float = 0.0,
    distance: float = DEFAULT_DISTANCE,
    pitch: float = DEFAULT_PITCH,
) -> CameraConfig:
    """Default angled overview suitable for warehouse: target at origin, look down."""
    return CameraConfig(
        width=width,
        height=height,
        target_x=target_x,
        target_y=target_y,
        target_z=target_z,
        distance=distance,
        yaw=0.0,
        pitch=pitch,
        roll=0.0,
    )


def _view_matrix_from_config(config: CameraConfig) -> list:
    if pb is None:
        raise RuntimeError("pybullet is not installed")
    target = [config.target_x, config.target_y, config.target_z]
    return pb.computeViewMatrixFromYawPitchRoll(
        target,
        config.distance,
        config.yaw,
        config.pitch,
        config.roll,
        UP_AXIS_Z,
    )


def _projection_matrix_from_config(config: CameraConfig) -> list:
    if pb is None:
        raise RuntimeError("pybullet is not installed")
    aspect = config.width / max(config.height, 1)
    fov_rad = config.fov_degrees * 3.141592653589793 / 180.0
    return pb.computeProjectionMatrixFOV(
        fov_rad,
        aspect,
        config.near,
        config.far,
    )


def _camera_pose_from_config(config: CameraConfig) -> CameraPose:
    view = _view_matrix_from_config(config)
    m = np.array(view, dtype=np.float64).reshape(4, 4, order="F")
    inv = np.linalg.inv(m)
    px, py, pz = float(inv[0, 3]), float(inv[1, 3]), float(inv[2, 3])
    return CameraPose(
        position_x=px,
        position_y=py,
        position_z=pz,
        yaw=config.yaw,
        pitch=config.pitch,
        roll=config.roll,
    )


def _intrinsics_from_config(config: CameraConfig) -> CameraIntrinsics:
    return CameraIntrinsics(
        width=config.width,
        height=config.height,
        fov=config.fov_degrees,
        near_plane=config.near,
        far_plane=config.far,
    )


def capture_frame(
    client_id: int,
    config: CameraConfig,
    renderer: Optional[int] = None,
) -> CapturedFrame:
    if pb is None:
        raise RuntimeError("pybullet is not installed")
    view = _view_matrix_from_config(config)
    proj = _projection_matrix_from_config(config)
    if renderer is None:
        renderer = pb.ER_TINY_RENDERER
    ts = time.time()
    result = pb.getCameraImage(
        config.width,
        config.height,
        viewMatrix=view,
        projectionMatrix=proj,
        renderer=renderer,
        physicsClientId=client_id,
    )
    w, h = result[0], result[1]
    rgba_flat = result[2]
    rgba = np.reshape(rgba_flat, (h, w, 4))
    rgb = np.ascontiguousarray(rgba[:, :, :3], dtype=np.uint8)
    pose = _camera_pose_from_config(config)
    intrinsics = _intrinsics_from_config(config)
    return CapturedFrame(
        rgb=rgb,
        width=w,
        height=h,
        camera_pose=pose,
        camera_intrinsics=intrinsics,
        timestamp=ts,
    )
