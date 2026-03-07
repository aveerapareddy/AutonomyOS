"""Minimal tests for simulator foundation."""

import pytest

try:
    import pybullet as pb
    PYBULLET_AVAILABLE = True
except ImportError:
    PYBULLET_AVAILABLE = False


@pytest.mark.skipif(not PYBULLET_AVAILABLE, reason="pybullet not installed")
def test_environment_initializes() -> None:
    from backend.simulator.environment import SimulationEnvironment

    env = SimulationEnvironment(use_gui=False)
    try:
        pose = env.get_robot_pose()
        assert pose.x == 0.0
        assert pose.y == 0.0
        assert pose.theta == 0.0
    finally:
        env.shutdown()


@pytest.mark.skipif(not PYBULLET_AVAILABLE, reason="pybullet not installed")
def test_target_exists() -> None:
    from backend.simulator.environment import SimulationEnvironment

    env = SimulationEnvironment(use_gui=False)
    try:
        target = env.get_target_pose()
        assert target.x == 5.0
        assert target.y == 3.0
        assert target.z > 0
    finally:
        env.shutdown()


@pytest.mark.skipif(not PYBULLET_AVAILABLE, reason="pybullet not installed")
def test_robot_pose_after_step() -> None:
    from backend.simulator.environment import (
        ACTION_FORWARD,
        SimulationEnvironment,
    )

    env = SimulationEnvironment(use_gui=False)
    try:
        for _ in range(10):
            env.step(ACTION_FORWARD)
        pose = env.get_robot_pose()
        assert pose.x > 0
        assert pose.y == 0.0
    finally:
        env.shutdown()
