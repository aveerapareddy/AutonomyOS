"""Simulation environment: PyBullet session, world, and robot."""

from dataclasses import dataclass
from typing import Optional, Tuple

try:
    import pybullet as pb
except ImportError:
    pb = None

from backend.simulator.robot import Robot, RobotPose
from backend.simulator.world_builder import build_world, BuiltWorld


# Default sim step for deterministic behavior.
DEFAULT_STEP_DT = 1.0 / 240.0

# Supported step() actions.
ACTION_FORWARD = "forward"
ACTION_BACKWARD = "backward"
ACTION_TURN_LEFT = "turn_left"
ACTION_TURN_RIGHT = "turn_right"
ACTION_STOP = "stop"


@dataclass
class TargetPose:
    """Target object position (e.g. red cube)."""

    x: float
    y: float
    z: float

    def as_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)


class SimulationEnvironment:
    """
    Single PyBullet environment: ground, obstacles, target, and one robot.
    Use reset() to restore initial state; shutdown() to disconnect.
    """

    def __init__(
        self,
        use_gui: bool = False,
        step_dt: float = DEFAULT_STEP_DT,
        robot_start: Optional[Tuple[float, float, float]] = None,
    ) -> None:
        if pb is None:
            raise RuntimeError("pybullet is not installed")
        self._step_dt = step_dt
        self._robot_start = robot_start or (0.0, 0.0, 0.0)
        self._client_id = pb.connect(pb.GUI if use_gui else pb.DIRECT)
        pb.setGravity(0, 0, -9.81, physicsClientId=self._client_id)
        self._world: Optional[BuiltWorld] = None
        self._robot: Optional[Robot] = None
        self._build()

    def _build(self) -> None:
        self._world = build_world()
        sx, sy, st = self._robot_start
        self._robot = Robot.create(start_x=sx, start_y=sy, start_theta=st)

    def reset(self) -> None:
        """Restore robot to start pose. World and target are static."""
        if self._robot is None or self._world is None:
            return
        sx, sy, st = self._robot_start
        self._robot.set_pose(sx, sy, st)

    def step(self, action: str) -> None:
        """Apply one movement action and step the simulation."""
        if self._robot is None:
            return
        cmd = action.strip().lower()
        if cmd == ACTION_FORWARD:
            self._robot.forward(self._step_dt)
        elif cmd == ACTION_BACKWARD:
            self._robot.backward(self._step_dt)
        elif cmd == ACTION_TURN_LEFT:
            self._robot.turn_left(self._step_dt)
        elif cmd == ACTION_TURN_RIGHT:
            self._robot.turn_right(self._step_dt)
        elif cmd == ACTION_STOP:
            self._robot.stop(self._step_dt)
        if pb is not None:
            pb.stepSimulation(physicsClientId=self._client_id)

    def get_robot_pose(self) -> RobotPose:
        if self._robot is None:
            raise RuntimeError("Environment not initialized")
        return self._robot.get_pose()

    def get_target_pose(self) -> TargetPose:
        if self._world is None:
            raise RuntimeError("Environment not initialized")
        x, y, z = self._world.target_position
        return TargetPose(x=x, y=y, z=z)

    def shutdown(self) -> None:
        """Disconnect the physics client."""
        if pb is not None and self._client_id is not None:
            pb.disconnect(physicsClientId=self._client_id)
            self._client_id = None
        self._robot = None
        self._world = None
