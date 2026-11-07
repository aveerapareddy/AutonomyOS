"""Camera config and frame capture tests."""

import math

import pytest

from backend.schemas.camera import (
    CameraConfig,
    CameraIntrinsics,
    CameraPose,
    CapturedFrame,
)
from backend.simulator.camera import default_camera_config

try:
    import pybullet as pb

    PYBULLET_AVAILABLE = True
except ImportError:
    PYBULLET_AVAILABLE = False


def test_camera_config_creation() -> None:
    config = CameraConfig(
        width=64,
        height=48,
        target_x=0.0,
        target_y=0.0,
        target_z=0.0,
        distance=20.0,
        yaw=0.0,
        pitch=-45.0,
        roll=0.0,
    )
    assert config.width == 64
    assert config.height == 48
    assert config.distance == 20.0
    assert config.pitch == -45.0


def test_default_camera_preset() -> None:
    config = default_camera_config()
    assert config.width == 640
    assert config.height == 480
    assert config.distance == 25.0
    assert config.pitch == -60.0
    assert config.target_x == 0.0 and config.target_y == 0.0


def test_default_camera_preset_custom_size() -> None:
    config = default_camera_config(width=320, height=240)
    assert config.width == 320
    assert config.height == 240


def test_camera_pose_creation() -> None:
    pose = CameraPose(
        position_x=1.0,
        position_y=-2.5,
        position_z=3.0,
        yaw=10.0,
        pitch=-45.0,
        roll=0.0,
    )
    assert pose.position_x == 1.0 and pose.position_y == -2.5 and pose.position_z == 3.0
    assert pose.yaw == 10.0 and pose.pitch == -45.0


def test_camera_intrinsics_creation() -> None:
    intr = CameraIntrinsics(width=640, height=480, fov=60.0, near_plane=0.1, far_plane=100.0)
    assert intr.width == 640 and intr.height == 480
    assert intr.fov == 60.0 and intr.near_plane == 0.1 and intr.far_plane == 100.0


def test_captured_frame_has_structured_metadata() -> None:
    import numpy as np

    rgb = np.zeros((10, 20, 3), dtype=np.uint8)
    pose = CameraPose(
        position_x=0.0,
        position_y=0.0,
        position_z=5.0,
        yaw=0.0,
        pitch=-30.0,
        roll=0.0,
    )
    intr = CameraIntrinsics(
        width=20,
        height=10,
        fov=60.0,
        near_plane=0.1,
        far_plane=500.0,
    )
    frame = CapturedFrame(
        rgb=rgb,
        width=20,
        height=10,
        camera_pose=pose,
        camera_intrinsics=intr,
        timestamp=1.234,
    )
    assert frame.camera_pose.position_z == 5.0
    assert frame.camera_intrinsics.fov == 60.0
    assert frame.timestamp == 1.234


@pytest.mark.skipif(not PYBULLET_AVAILABLE, reason="pybullet not installed")
def test_capture_frame_returns_expected_dimensions() -> None:
    from backend.simulator.environment import SimulationEnvironment

    env = SimulationEnvironment(use_gui=False)
    try:
        config = CameraConfig(
            width=80,
            height=60,
            target_x=0.0,
            target_y=0.0,
            target_z=0.0,
            distance=25.0,
        )
        frame = env.capture_frame(config)
        assert frame.width == 80
        assert frame.height == 60
        assert frame.rgb.shape == (60, 80, 3)
    finally:
        env.shutdown()


@pytest.mark.skipif(not PYBULLET_AVAILABLE, reason="pybullet not installed")
def test_capture_frame_data_non_empty() -> None:
    from backend.simulator.environment import SimulationEnvironment

    env = SimulationEnvironment(use_gui=False)
    try:
        config = default_camera_config(width=64, height=64)
        frame = env.capture_frame(config)
        assert frame.rgb.size > 0
        assert frame.rgb.dtype.name in ("uint8", "uint16", "int32") or "int" in frame.rgb.dtype.name
    finally:
        env.shutdown()


@pytest.mark.skipif(not PYBULLET_AVAILABLE, reason="pybullet not installed")
def test_default_preset_works() -> None:
    from backend.simulator.environment import SimulationEnvironment

    env = SimulationEnvironment(use_gui=False)
    try:
        config = default_camera_config(width=100, height=100)
        frame = env.capture_frame(config)
        assert isinstance(frame, CapturedFrame)
        assert frame.width == 100 and frame.height == 100
        assert frame.camera_pose is not None
        assert frame.camera_intrinsics is not None
        assert frame.camera_intrinsics.width == 100
        assert frame.camera_intrinsics.height == 100
        assert frame.camera_intrinsics.fov == config.fov_degrees
        assert frame.camera_intrinsics.near_plane == config.near
        assert frame.camera_intrinsics.far_plane == config.far
        assert isinstance(frame.timestamp, float)
        assert frame.camera_pose.yaw == config.yaw
        assert frame.camera_pose.pitch == config.pitch
        assert frame.camera_pose.roll == config.roll
    finally:
        env.shutdown()


@pytest.mark.skipif(not PYBULLET_AVAILABLE, reason="pybullet not installed")
def test_capture_frame_metadata_matches_config() -> None:
    from backend.simulator.environment import SimulationEnvironment

    env = SimulationEnvironment(use_gui=False)
    try:
        config = CameraConfig(
            width=64,
            height=48,
            target_x=1.0,
            target_y=2.0,
            target_z=0.5,
            distance=10.0,
            yaw=15.0,
            pitch=-30.0,
            roll=5.0,
            fov_degrees=45.0,
            near=0.2,
            far=200.0,
        )
        frame = env.capture_frame(config)
        assert frame.camera_intrinsics.fov == 45.0
        assert frame.camera_intrinsics.near_plane == 0.2
        assert frame.camera_intrinsics.far_plane == 200.0
        assert frame.camera_pose.yaw == 15.0
        assert frame.camera_pose.pitch == -30.0
        assert frame.camera_pose.roll == 5.0
        assert math.isfinite(frame.camera_pose.position_x)
        assert math.isfinite(frame.camera_pose.position_y)
        assert math.isfinite(frame.camera_pose.position_z)
    finally:
        env.shutdown()
