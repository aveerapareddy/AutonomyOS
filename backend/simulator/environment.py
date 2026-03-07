"""Simulation environment: PyBullet session, world, and robot."""

from dataclasses import dataclass
from typing import List, Optional, Tuple, Union

try:
    import pybullet as pb
except ImportError:
    pb = None

from backend.schemas.world import WorldObject
from backend.simulator.actions import RobotAction
from backend.simulator.robot import Robot, RobotPose
from backend.simulator.world_builder import build_world, BuiltWorld


# Default sim step for deterministic behavior.
DEFAULT_STEP_DT = 1.0 / 240.0


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

    def step(self, action: Union[RobotAction, str]) -> None:
        """Apply one movement action and step the simulation."""
        if self._robot is None:
            return
        cmd = RobotAction(action) if isinstance(action, str) else action
        if cmd == RobotAction.FORWARD:
            self._robot.forward(self._step_dt)
        elif cmd == RobotAction.BACKWARD:
            self._robot.backward(self._step_dt)
        elif cmd == RobotAction.TURN_LEFT:
            self._robot.turn_left(self._step_dt)
        elif cmd == RobotAction.TURN_RIGHT:
            self._robot.turn_right(self._step_dt)
        elif cmd == RobotAction.STOP:
            self._robot.stop(self._step_dt)
        if pb is not None:
            pb.stepSimulation(physicsClientId=self._client_id)

    def get_robot_pose(self) -> RobotPose:
        if self._robot is None:
            raise RuntimeError("Environment not initialized")
        return self._robot.get_pose()

    def get_world_bounds(self) -> Tuple[float, float, float, float]:
        """Return (min_x, max_x, min_y, max_y)."""
        if self._world is None:
            raise RuntimeError("Environment not initialized")
        return self._world.world_bounds

    def get_obstacles(self) -> List[Tuple[float, float]]:
        """Return list of obstacle (x, y) positions."""
        if self._world is None:
            raise RuntimeError("Environment not initialized")
        return list(self._world.obstacle_positions)

    def get_obstacle_types(self) -> List[str]:
        """Return list of obstacle type labels (same order as get_obstacles())."""
        if self._world is None:
            raise RuntimeError("Environment not initialized")
        return list(self._world.obstacle_types)

    def get_obstacle_objects(self) -> List[WorldObject]:
        """Return typed obstacle descriptors (single source of truth)."""
        if self._world is None:
            raise RuntimeError("Environment not initialized")
        return list(self._world.obstacle_objects)

    def get_target_object(self) -> WorldObject:
        """Return typed target descriptor."""
        if self._world is None:
            raise RuntimeError("Environment not initialized")
        return self._world.target_object

    def get_target_pose(self) -> TargetPose:
        if self._world is None:
            raise RuntimeError("Environment not initialized")
        x, y = self._world.target_position
        return TargetPose(x=x, y=y, z=self._world.target_z)

    def shutdown(self) -> None:
        """Disconnect the physics client."""
        if pb is not None and self._client_id is not None:
            pb.disconnect(physicsClientId=self._client_id)
            self._client_id = None
        self._robot = None
        self._world = None
