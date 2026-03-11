"""Perception backend protocol and facade for backend selection."""

from typing import List, Protocol, Union

import numpy as np

from backend.schemas.perception import PerceptionRequest, PerceptionResult
from backend.schemas.world import WorldObject


class PerceptionBackend(Protocol):
    """Protocol for perception backends. Implement from_objects and/or from_image as applicable."""

    def perceive_from_objects(
        self,
        obstacle_objects: List[WorldObject],
        target_object: WorldObject,
        request: PerceptionRequest | None = None,
    ) -> PerceptionResult:
        ...

    def perceive_image(
        self,
        image: Union[str, np.ndarray],
        request: PerceptionRequest | None = None,
        model_path: str = "yolov8n.pt",
        confidence: float = 0.25,
    ) -> PerceptionResult:
        ...


class PerceptionFacade:
    """
    Single entry point for perception: selects backend per operation.
    Object-based path uses metadata backend; image path uses YOLO when available.
    """

    def __init__(self) -> None:
        from backend.agents.perception_backends.metadata_backend import MetadataPerceptionBackend
        from backend.agents.perception_backends.yolo_backend import (
            YoloPerceptionBackend,
            yolo_available,
        )

        self._metadata = MetadataPerceptionBackend()
        self._yolo: YoloPerceptionBackend | None = YoloPerceptionBackend() if yolo_available() else None

    def perceive_from_objects(
        self,
        obstacle_objects: List[WorldObject],
        target_object: WorldObject,
        request: PerceptionRequest | None = None,
    ) -> PerceptionResult:
        return self._metadata.perceive_from_objects(
            obstacle_objects,
            target_object,
            request,
        )

    def perceive_image(
        self,
        image: Union[str, np.ndarray],
        request: PerceptionRequest | None = None,
        model_path: str = "yolov8n.pt",
        confidence: float = 0.25,
    ) -> PerceptionResult:
        if self._yolo is not None:
            return self._yolo.perceive_image(
                image,
                request=request,
                model_path=model_path,
                confidence=confidence,
            )
        return PerceptionResult(
            detected_targets=[],
            detected_obstacles=[],
            message="YOLO backend unavailable",
        )

    def get_yolo_backend_status(self) -> str:
        return "available" if self._yolo is not None else "unavailable"
