"""Robot abstraction with basic kinematic movement primitives."""

import math
from dataclasses import dataclass
from typing import Tuple

try:
    import pybullet as pb
except ImportError:
    pb = None

# Kinematic parameters. Deterministic.
LINEAR_SPEED = 0.5
ANGULAR_SPEED = 1.0  # rad/s
ROBOT_HALF_EXTENTS = (0.2, 0.15, 0.1)


@dataclass
class RobotPose:
    """Robot state in the plane."""

    x: float
    y: float
    theta: float

    def as_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.theta)


class Robot:
    """
    Simple kinematic robot: a box body whose pose is updated by movement commands.
    No wheel or force model; pose is set directly.
    """

    def __init__(
        self,
        body_id: int,
        initial_x: float = 0.0,
        initial_y: float = 0.0,
        initial_theta: float = 0.0,
    ) -> None:
        self._body_id = body_id
        self._x = initial_x
        self._y = initial_y
        self._theta = initial_theta
        self._sync_to_body()

    @classmethod
    def create(
        cls,
        start_x: float = 0.0,
        start_y: float = 0.0,
        start_theta: float = 0.0,
    ) -> "Robot":
        """Create the robot body in the current PyBullet session and return a Robot instance."""
        if pb is None:
            raise RuntimeError("pybullet is not installed")
        half = ROBOT_HALF_EXTENTS
        z = half[2]
        col = pb.createCollisionShape(pb.GEOM_BOX, halfExtents=half)
        body_id = pb.createMultiBody(
            baseMass=1.0,
            baseCollisionShapeIndex=col,
            basePosition=(start_x, start_y, z),
            baseOrientation=pb.getQuaternionFromEuler([0, 0, start_theta]),
        )
        return cls(body_id, start_x, start_y, start_theta)

    def _sync_to_body(self) -> None:
        if pb is None:
            return
        half = ROBOT_HALF_EXTENTS
        pos = (self._x, self._y, half[2])
        orn = pb.getQuaternionFromEuler([0, 0, self._theta])
        pb.resetBasePositionAndOrientation(self._body_id, pos, orn)

    def forward(self, dt: float) -> None:
        self._x += LINEAR_SPEED * math.cos(self._theta) * dt
        self._y += LINEAR_SPEED * math.sin(self._theta) * dt
        self._sync_to_body()

    def backward(self, dt: float) -> None:
        self._x -= LINEAR_SPEED * math.cos(self._theta) * dt
        self._y -= LINEAR_SPEED * math.sin(self._theta) * dt
        self._sync_to_body()

    def turn_left(self, dt: float) -> None:
        self._theta += ANGULAR_SPEED * dt
        self._sync_to_body()

    def turn_right(self, dt: float) -> None:
        self._theta -= ANGULAR_SPEED * dt
        self._sync_to_body()

    def stop(self, dt: float = 0.0) -> None:
        """No-op for kinematic model; state unchanged."""
        pass

    def get_pose(self) -> RobotPose:
        return RobotPose(x=self._x, y=self._y, theta=self._theta)

    def set_pose(self, x: float, y: float, theta: float) -> None:
        """Reset pose (e.g. for environment reset)."""
        self._x = x
        self._y = y
        self._theta = theta
        self._sync_to_body()
