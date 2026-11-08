"""Perception backends: metadata (rule-based) and YOLO (vision)."""

from backend.agents.perception_backends.base import PerceptionBackend, PerceptionFacade
from backend.agents.perception_backends.metadata_backend import (
    MetadataPerceptionBackend,
    perceive as metadata_perceive,
    perceive_from_objects as metadata_perceive_from_objects,
)
from backend.agents.perception_backends.yolo_backend import (
    YoloPerceptionBackend,
    perceive_image as yolo_perceive_image,
    yolo_available,
)

PERCEPTION_MODES = ("metadata", "yolo")

__all__ = [
    "PERCEPTION_MODES",
    "PerceptionBackend",
    "PerceptionFacade",
    "MetadataPerceptionBackend",
    "YoloPerceptionBackend",
    "metadata_perceive",
    "metadata_perceive_from_objects",
    "yolo_perceive_image",
    "yolo_available",
]
