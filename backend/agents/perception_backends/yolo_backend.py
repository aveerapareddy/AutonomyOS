"""
YOLO-backed perception from image input. Returns PerceptionResult contract.
Backlog: map detector classes to internal semantics (target_candidate, obstacle, ignored)
before using in mission execution.
"""

from typing import Any, List, Union

import numpy as np

from backend.schemas.perception import (
    DetectedObject,
    PerceptionRequest,
    PerceptionResult,
)
from backend.schemas.world import WorldObject

try:
    from ultralytics import YOLO

    _YOLO_IMPORT_OK = True
except ImportError:
    _YOLO_IMPORT_OK = False

DEFAULT_MODEL = "yolov8n.pt"
DEFAULT_CONFIDENCE = 0.25


def yolo_available() -> bool:
    return _YOLO_IMPORT_OK


class YoloPerceptionBackend:
    """Backend that produces PerceptionResult from image input via YOLO. No object input."""

    def perceive_from_objects(
        self,
        obstacle_objects: List[WorldObject],
        target_object: WorldObject,
        request: PerceptionRequest | None = None,
    ) -> PerceptionResult:
        return PerceptionResult(
            detected_targets=[],
            detected_obstacles=[],
            message="YOLO backend does not support object input",
        )

    def perceive_image(
        self,
        image: Union[str, np.ndarray],
        request: PerceptionRequest | None = None,
        model_path: str = DEFAULT_MODEL,
        confidence: float = DEFAULT_CONFIDENCE,
    ) -> PerceptionResult:
        return perceive_image(
            image,
            request=request,
            model_path=model_path,
            confidence=confidence,
        )


def _image_to_numpy(image: Union[str, np.ndarray]) -> np.ndarray:
    if isinstance(image, np.ndarray):
        return image
    try:
        from PIL import Image

        img = Image.open(image).convert("RGB")
        return np.array(img)
    except Exception:
        raise ValueError(f"Cannot load image from {image!r}")


def _run_inference(model: Any, image: np.ndarray, conf: float) -> Any:
    results = model.predict(image, conf=conf, verbose=False)
    return results[0] if results else None


def _results_to_detections(
    result: Any,
    height: int,
    width: int,
    request: PerceptionRequest,
) -> tuple[List[DetectedObject], List[DetectedObject]]:
    targets: List[DetectedObject] = []
    obstacles: List[DetectedObject] = []
    if result is None or result.boxes is None:
        return targets, obstacles

    boxes = result.boxes
    n = len(boxes)
    if n == 0:
        return targets, obstacles

    def _to_np(t):
        if t is None:
            return np.array([])
        if hasattr(t, "cpu"):
            return t.cpu().numpy()
        if hasattr(t, "numpy"):
            return t.numpy()
        return np.array(t)

    xyxy = _to_np(boxes.xyxy)
    conf = _to_np(boxes.conf)
    cls_ids = _to_np(boxes.cls)
    names = result.names or {}

    for i in range(n):
        x1, y1, x2, y2 = xyxy[i]
        cx = (float(x1) + float(x2)) / 2.0 / max(width, 1)
        cy = (float(y1) + float(y2)) / 2.0 / max(height, 1)
        cx = max(0.0, min(1.0, cx))
        cy = max(0.0, min(1.0, cy))
        obj_type = names.get(int(cls_ids[i]), "obstacle")
        if isinstance(obj_type, int):
            obj_type = "obstacle"
        conf_val = float(conf[i])
        det = DetectedObject(
            object_id=f"det_{i}",
            object_type=obj_type,
            x=cx,
            y=cy,
            confidence=round(conf_val, 4),
        )
        if request.include_obstacles:
            obstacles.append(det)

    return targets, obstacles


def perceive_image(
    image: Union[str, np.ndarray],
    request: PerceptionRequest | None = None,
    model_path: str = DEFAULT_MODEL,
    confidence: float = DEFAULT_CONFIDENCE,
) -> PerceptionResult:
    """
    Run YOLO on an image and return PerceptionResult.
    image: path to image file or (H, W, 3) numpy array in RGB.
    x, y in result are normalized 0-1 (center of box).
    """
    if not _YOLO_IMPORT_OK:
        return PerceptionResult(
            detected_targets=[],
            detected_obstacles=[],
            message="YOLO backend unavailable: ultralytics not installed",
        )
    req = request or PerceptionRequest()
    arr = _image_to_numpy(image)
    if arr.ndim != 3 or arr.shape[2] != 3:
        return PerceptionResult(
            detected_targets=[],
            detected_obstacles=[],
            message="Image must be RGB (H, W, 3)",
        )
    height, width = arr.shape[0], arr.shape[1]
    try:
        model = YOLO(model_path)
    except Exception as e:
        return PerceptionResult(
            detected_targets=[],
            detected_obstacles=[],
            message=f"YOLO model load failed: {e}",
        )
    result = _run_inference(model, arr, confidence)
    targets, obstacles = _results_to_detections(result, height, width, req)
    return PerceptionResult(
        detected_targets=targets,
        detected_obstacles=obstacles,
    )
