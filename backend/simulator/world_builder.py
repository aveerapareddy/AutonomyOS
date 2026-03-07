"""Deterministic warehouse-like world construction for PyBullet."""

from dataclasses import dataclass
from typing import List, Tuple

# Lazy import so tests can run without PyBullet if needed
try:
    import pybullet as pb
except ImportError:
    pb = None


@dataclass
class BuiltWorld:
    """Ids and positions of built world elements."""

    ground_id: int
    obstacle_ids: List[int]
    target_id: int
    target_position: Tuple[float, float, float]


# Fixed layout for reproducibility. Parameterize later for scenario generation.
_FLOOR_EXTENT = 20.0
_OBSTACLE_HALF = (0.5, 0.5, 0.5)
_TARGET_HALF = (0.15, 0.15, 0.15)
_TARGET_XY = (5.0, 3.0)
_WALL_HALF_X = 0.3
_WALL_HALF_Y = 4.0
_WALL_HALF_Z = 0.5


def build_world() -> BuiltWorld:
    """
    Create a flat world with static obstacles and one target cube.
    Deterministic: same layout every call.
    """
    if pb is None:
        raise RuntimeError("pybullet is not installed")

    ground_id = _create_ground()
    obstacle_ids = _create_obstacles()
    target_id, target_position = _create_target()

    return BuiltWorld(
        ground_id=ground_id,
        obstacle_ids=obstacle_ids,
        target_id=target_id,
        target_position=target_position,
    )


def _create_ground() -> int:
    plane = pb.createCollisionShape(pb.GEOM_PLANE)
    body = pb.createMultiBody(0, plane)
    return body


def _create_obstacles() -> List[int]:
    """Aisle-like barriers: two parallel walls, one block."""
    ids_ = []
    shape = pb.createCollisionShape(
        pb.GEOM_BOX,
        halfExtents=[_WALL_HALF_X, _WALL_HALF_Y, _WALL_HALF_Z],
    )
    # Left wall
    ids_.append(
        pb.createMultiBody(
            0,
            shape,
            basePosition=(-3.0, 0.0, _WALL_HALF_Z),
        )
    )
    # Right wall
    ids_.append(
        pb.createMultiBody(
            0,
            shape,
            basePosition=(3.0, 0.0, _WALL_HALF_Z),
        )
    )
    # Block in the way
    block = pb.createCollisionShape(pb.GEOM_BOX, halfExtents=_OBSTACLE_HALF)
    ids_.append(
        pb.createMultiBody(
            0,
            block,
            basePosition=(1.0, 1.0, _OBSTACLE_HALF[2]),
        )
    )
    return ids_


def _create_target() -> Tuple[int, Tuple[float, float, float]]:
    """One red cube at a fixed position."""
    half = _TARGET_HALF
    position = (_TARGET_XY[0], _TARGET_XY[1], half[2])
    col = pb.createCollisionShape(pb.GEOM_BOX, halfExtents=half)
    vis = pb.createVisualShape(
        pb.GEOM_BOX,
        halfExtents=half,
        rgbaColor=(0.9, 0.2, 0.2, 1.0),
    )
    body = pb.createMultiBody(
        0,
        col,
        vis,
        basePosition=position,
    )
    return body, position
