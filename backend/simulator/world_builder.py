"""Deterministic warehouse-like world construction for PyBullet."""

from dataclasses import dataclass
from typing import List, Tuple

# Lazy import so tests can run without PyBullet if needed
try:
    import pybullet as pb
except ImportError:
    pb = None


# World bounds (min_x, max_x, min_y, max_y). Fixed for reproducibility.
WORLD_BOUNDS = (-10.0, 10.0, -10.0, 10.0)


@dataclass
class BuiltWorld:
    """Ids and 2D positions of built world elements."""

    ground_id: int
    obstacle_ids: List[int]
    obstacle_positions: List[Tuple[float, float]]
    target_id: int
    target_position: Tuple[float, float]
    target_z: float
    world_bounds: Tuple[float, float, float, float]


# Fixed layout for reproducibility. Parameterize later for scenario generation.
_FLOOR_EXTENT = 20.0
_OBSTACLE_HALF = (0.5, 0.5, 0.5)
_TARGET_HALF = (0.15, 0.15, 0.15)
_TARGET_XY = (5.0, 3.0)
_WALL_HALF_X = 0.3
_WALL_HALF_Y = 4.0
_WALL_HALF_Z = 0.5

# Obstacle (x, y) positions; z comes from half extents.
_WALL_LEFT_XY = (-3.0, 0.0)
_WALL_RIGHT_XY = (3.0, 0.0)
_BLOCK_XY = (1.0, 1.0)


def build_world() -> BuiltWorld:
    """
    Create a flat world with static obstacles and one target cube.
    Deterministic: same layout every call.
    """
    if pb is None:
        raise RuntimeError("pybullet is not installed")

    ground_id = _create_ground()
    obstacle_ids, obstacle_positions = _create_obstacles()
    target_id, target_position_2d, target_z = _create_target()

    return BuiltWorld(
        ground_id=ground_id,
        obstacle_ids=obstacle_ids,
        obstacle_positions=obstacle_positions,
        target_id=target_id,
        target_position=target_position_2d,
        target_z=target_z,
        world_bounds=WORLD_BOUNDS,
    )


def _create_ground() -> int:
    plane = pb.createCollisionShape(pb.GEOM_PLANE)
    body = pb.createMultiBody(0, plane)
    return body


def _create_obstacles() -> Tuple[List[int], List[Tuple[float, float]]]:
    """Aisle-like barriers: two parallel walls, one block."""
    ids_: List[int] = []
    positions: List[Tuple[float, float]] = []
    shape = pb.createCollisionShape(
        pb.GEOM_BOX,
        halfExtents=[_WALL_HALF_X, _WALL_HALF_Y, _WALL_HALF_Z],
    )
    ids_.append(
        pb.createMultiBody(
            0,
            shape,
            basePosition=(_WALL_LEFT_XY[0], _WALL_LEFT_XY[1], _WALL_HALF_Z),
        )
    )
    positions.append(_WALL_LEFT_XY)
    ids_.append(
        pb.createMultiBody(
            0,
            shape,
            basePosition=(_WALL_RIGHT_XY[0], _WALL_RIGHT_XY[1], _WALL_HALF_Z),
        )
    )
    positions.append(_WALL_RIGHT_XY)
    block = pb.createCollisionShape(pb.GEOM_BOX, halfExtents=_OBSTACLE_HALF)
    ids_.append(
        pb.createMultiBody(
            0,
            block,
            basePosition=(_BLOCK_XY[0], _BLOCK_XY[1], _OBSTACLE_HALF[2]),
        )
    )
    positions.append(_BLOCK_XY)
    return ids_, positions


def _create_target() -> Tuple[int, Tuple[float, float], float]:
    """One red cube at a fixed position. Returns (body_id, (x, y), z)."""
    half = _TARGET_HALF
    x, y = _TARGET_XY
    z = half[2]
    position_3d = (x, y, z)
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
        basePosition=position_3d,
    )
    return body, (x, y), z
