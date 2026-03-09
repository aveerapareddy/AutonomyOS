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
    from backend.simulator.actions import RobotAction
    from backend.simulator.environment import SimulationEnvironment

    env = SimulationEnvironment(use_gui=False)
    try:
        for _ in range(10):
            env.step(RobotAction.FORWARD)
        pose = env.get_robot_pose()
        assert pose.x > 0
        assert pose.y == 0.0
    finally:
        env.shutdown()


@pytest.mark.skipif(not PYBULLET_AVAILABLE, reason="pybullet not installed")
def test_environment_with_world_layout_uses_scenario_geometry() -> None:
    from backend.simulator.environment import SimulationEnvironment
    from backend.simulator.world_builder import WorldLayoutSpec

    spec = WorldLayoutSpec(
        world_bounds=(-5.0, 5.0, -5.0, 5.0),
        obstacle_positions=[(1.0, 1.0), (-2.0, 0.0)],
        obstacle_types=["block", "wall"],
        target_position=(3.0, 4.0),
    )
    env = SimulationEnvironment(use_gui=False, world_layout=spec)
    try:
        bounds = env.get_world_bounds()
        assert bounds == (-5.0, 5.0, -5.0, 5.0)
        target = env.get_target_pose()
        assert target.x == 3.0
        assert target.y == 4.0
        obstacles = env.get_obstacles()
        assert len(obstacles) == 2
        assert (1.0, 1.0) in obstacles
        assert (-2.0, 0.0) in obstacles
    finally:
        env.shutdown()


@pytest.mark.skipif(not PYBULLET_AVAILABLE, reason="pybullet not installed")
def test_default_environment_unchanged_without_world_layout() -> None:
    from backend.simulator.environment import SimulationEnvironment
    from backend.simulator.world_builder import WORLD_BOUNDS

    env = SimulationEnvironment(use_gui=False)
    try:
        assert env.get_world_bounds() == WORLD_BOUNDS
        target = env.get_target_pose()
        assert target.x == 5.0
        assert target.y == 3.0
    finally:
        env.shutdown()
