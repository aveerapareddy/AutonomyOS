"""Camera config and frame capture tests."""

import pytest

from backend.schemas.camera import CameraConfig, CapturedFrame
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
        assert frame.metadata is not None
    finally:
        env.shutdown()
