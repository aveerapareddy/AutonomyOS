"""Rule-based perception from world metadata. Swappable with YOLO later."""

from typing import List, Tuple

from backend.core.constants import OBSTACLE_CONFIDENCE_DEFAULT, TARGET_CONFIDENCE_DEFAULT
from backend.schemas.perception import (
    DetectedObject,
    PerceptionRequest,
    PerceptionResult,
)
from backend.schemas.world import WorldObject


def perceive(
    obstacle_positions: List[Tuple[float, float]],
    obstacle_types: List[str],
    target_x: float,
    target_y: float,
    request: PerceptionRequest | None = None,
) -> PerceptionResult:
    """
    Produce detections from world metadata. Phase-1: deterministic, no vision.
    Same contract as a future YOLO-backed implementation.
    """
    req = request or PerceptionRequest()
    targets: List[DetectedObject] = []
    obstacles: List[DetectedObject] = []

    if req.include_targets:
        targets.append(
            DetectedObject(
                object_id="target",
                object_type="target",
                x=target_x,
                y=target_y,
                confidence=TARGET_CONFIDENCE_DEFAULT,
            )
        )

    if req.include_obstacles:
        for i, (x, y) in enumerate(obstacle_positions):
            obj_type = obstacle_types[i] if i < len(obstacle_types) else "obstacle"
            obstacles.append(
                DetectedObject(
                    object_id=f"obstacle_{i}",
                    object_type=obj_type,
                    x=x,
                    y=y,
                    confidence=OBSTACLE_CONFIDENCE_DEFAULT,
                )
            )

    return PerceptionResult(
        detected_targets=targets,
        detected_obstacles=obstacles,
    )


def perceive_from_objects(
    obstacle_objects: List[WorldObject],
    target_object: WorldObject,
    request: PerceptionRequest | None = None,
) -> PerceptionResult:
    """Produce detections from typed world objects. Single source of truth, no parallel lists."""
    req = request or PerceptionRequest()
    targets: List[DetectedObject] = []
    obstacles: List[DetectedObject] = []

    if req.include_targets:
        targets.append(
            DetectedObject(
                object_id=target_object.object_id,
                object_type=target_object.object_type,
                x=target_object.x,
                y=target_object.y,
                confidence=TARGET_CONFIDENCE_DEFAULT,
            )
        )

    if req.include_obstacles:
        for o in obstacle_objects:
            obstacles.append(
                DetectedObject(
                    object_id=o.object_id,
                    object_type=o.object_type,
                    x=o.x,
                    y=o.y,
                    confidence=OBSTACLE_CONFIDENCE_DEFAULT,
                )
            )

    return PerceptionResult(
        detected_targets=targets,
        detected_obstacles=obstacles,
    )
