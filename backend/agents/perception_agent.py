"""
Perception agent: stable contract (PerceptionRequest / PerceptionResult).
PerceptionFacade selects backend per operation (metadata for objects, YOLO for image).
"""

from typing import List, Union

import numpy as np

from backend.schemas.perception import PerceptionRequest, PerceptionResult
from backend.schemas.world import WorldObject

from backend.agents.perception_backends import metadata_perceive, metadata_perceive_from_objects
from backend.agents.perception_backends.base import PerceptionFacade

_facade = PerceptionFacade()


def perceive(
    obstacle_positions: List[tuple[float, float]],
    obstacle_types: List[str],
    target_x: float,
    target_y: float,
    request: PerceptionRequest | None = None,
) -> PerceptionResult:
    """Metadata-backed perception from positions and types. Default for orchestration."""
    return metadata_perceive(
        obstacle_positions,
        obstacle_types,
        target_x,
        target_y,
        request,
    )


def perceive_from_objects(
    obstacle_objects: List[WorldObject],
    target_object: WorldObject,
    request: PerceptionRequest | None = None,
) -> PerceptionResult:
    """Metadata-backed perception from world objects. Used by orchestrator."""
    return _facade.perceive_from_objects(obstacle_objects, target_object, request)


def perceive_image(
    image: Union[str, np.ndarray],
    request: PerceptionRequest | None = None,
    model_path: str = "yolov8n.pt",
    confidence: float = 0.25,
) -> PerceptionResult:
    """YOLO-backed perception from image. Returns PerceptionResult; empty if YOLO unavailable."""
    return _facade.perceive_image(
        image,
        request=request,
        model_path=model_path,
        confidence=confidence,
    )


def get_yolo_backend_status() -> str:
    """Report whether the YOLO (image) backend is available. 'available' or 'unavailable'."""
    return _facade.get_yolo_backend_status()
