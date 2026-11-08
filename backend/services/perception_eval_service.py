"""Perception evaluation: compare simulator truth with perception outputs."""

from typing import List, Optional

from backend.schemas.perception import DetectedObject
from backend.schemas.perception_eval import PerceptionEvalResult, PerceptionMatch
from backend.schemas.projection import ProjectedDetection
from backend.schemas.world import WorldObject

POSITION_TOLERANCE_DEFAULT = 0.5

PROJECTED_EVAL_NOTE = (
    "Approximate evaluation: projected image detections vs truth; not physically accurate."
)

_YOLO_LABEL_TO_FAMILY: dict[str, str] = {
    "person": "obstacle",
    "car": "obstacle",
    "truck": "obstacle",
    "bus": "obstacle",
    "bicycle": "obstacle",
    "motorcycle": "obstacle",
    "boat": "obstacle",
}


def truth_semantic_family(truth_type: str) -> str:
    if truth_type == "target":
        return "target"
    return "obstacle"


def predicted_semantic_family(detector_label: str) -> str:
    key = detector_label.lower().strip()
    if key in ("target", "target_candidate"):
        return "target"
    if key in _YOLO_LABEL_TO_FAMILY:
        return _YOLO_LABEL_TO_FAMILY[key]
    if key in ("wall", "block", "obstacle"):
        return "obstacle"
    return "obstacle"


def _precision_recall(matched: int, truth_n: int, pred_n: int) -> tuple[Optional[float], Optional[float]]:
    precision = matched / pred_n if pred_n > 0 else None
    recall = matched / truth_n if truth_n > 0 else None
    return precision, recall


def truth_objects_from_world(
    target_object: WorldObject,
    obstacle_objects: List[WorldObject],
) -> List[WorldObject]:
    out: List[WorldObject] = [target_object]
    out.extend(obstacle_objects)
    return out


def _flatten_predictions(
    detected_targets: List[DetectedObject],
    detected_obstacles: List[DetectedObject],
) -> List[DetectedObject]:
    return list(detected_targets) + list(detected_obstacles)


def _distance_sq(ax: float, ay: float, bx: float, by: float) -> float:
    return (ax - bx) ** 2 + (ay - by) ** 2


def evaluate_perception(
    truth_objects: List[WorldObject],
    detected_targets: List[DetectedObject],
    detected_obstacles: List[DetectedObject],
    backend_name: str = "metadata",
    position_tolerance: float = POSITION_TOLERANCE_DEFAULT,
) -> PerceptionEvalResult:
    """Metadata-style detections: world-space x,y; match by exact object_type and position."""
    predicted = _flatten_predictions(detected_targets, detected_obstacles)
    truth_count = len(truth_objects)
    predicted_count = len(predicted)
    tolerance_sq = position_tolerance**2
    used_pred: set[int] = set()
    object_matches: List[PerceptionMatch] = []

    for truth in truth_objects:
        best_idx: int | None = None
        best_dist_sq = float("inf")
        for i, pred in enumerate(predicted):
            if i in used_pred:
                continue
            if pred.object_type != truth.object_type:
                continue
            d2 = _distance_sq(truth.x, truth.y, pred.x, pred.y)
            if d2 <= tolerance_sq and d2 < best_dist_sq:
                best_dist_sq = d2
                best_idx = i

        if best_idx is not None:
            used_pred.add(best_idx)
            pred = predicted[best_idx]
            object_matches.append(
                PerceptionMatch(
                    truth_object_id=truth.object_id,
                    predicted_object_id=str(pred.object_id),
                    truth_type=truth.object_type,
                    predicted_type=pred.object_type,
                    matched=True,
                    confidence=pred.confidence,
                )
            )
        else:
            object_matches.append(
                PerceptionMatch(
                    truth_object_id=truth.object_id,
                    predicted_object_id=None,
                    truth_type=truth.object_type,
                    predicted_type=None,
                    matched=False,
                    confidence=None,
                )
            )

    for i, pred in enumerate(predicted):
        if i in used_pred:
            continue
        object_matches.append(
            PerceptionMatch(
                truth_object_id=None,
                predicted_object_id=str(pred.object_id),
                truth_type=None,
                predicted_type=pred.object_type,
                matched=False,
                confidence=pred.confidence,
            )
        )

    matched_count = sum(1 for m in object_matches if m.matched)
    prec, rec = _precision_recall(matched_count, truth_count, predicted_count)
    return PerceptionEvalResult(
        backend_name=backend_name,
        truth_count=truth_count,
        predicted_count=predicted_count,
        matched_count=matched_count,
        unmatched_truth_count=truth_count - matched_count,
        unmatched_prediction_count=predicted_count - matched_count,
        object_matches=object_matches,
        message=None,
        precision=prec,
        recall=rec,
    )


def _projected_world_xy(item: ProjectedDetection) -> tuple[float, float] | None:
    p = item.projection
    if not p.valid:
        return None
    return (p.world_x, p.world_y)


def evaluate_projected_detections(
    truth_objects: List[WorldObject],
    projected_detections: List[ProjectedDetection],
    position_tolerance: float = POSITION_TOLERANCE_DEFAULT,
    backend_name: str = "yolo_projected",
) -> PerceptionEvalResult:
    """
    Match projected (approximate world) positions to truth using semantic family compatibility.
    """
    truth_count = len(truth_objects)
    predicted_count = len(projected_detections)
    tolerance_sq = position_tolerance**2
    used_idx: set[int] = set()
    object_matches: List[PerceptionMatch] = []

    for truth in truth_objects:
        tf = truth_semantic_family(truth.object_type)
        best_i: int | None = None
        best_d2 = float("inf")
        for i, item in enumerate(projected_detections):
            if i in used_idx:
                continue
            wxy = _projected_world_xy(item)
            if wxy is None:
                continue
            if predicted_semantic_family(item.original.object_type) != tf:
                continue
            d2 = _distance_sq(truth.x, truth.y, wxy[0], wxy[1])
            if d2 <= tolerance_sq and d2 < best_d2:
                best_d2 = d2
                best_i = i

        if best_i is not None:
            used_idx.add(best_i)
            pred = projected_detections[best_i].original
            object_matches.append(
                PerceptionMatch(
                    truth_object_id=truth.object_id,
                    predicted_object_id=str(pred.object_id),
                    truth_type=truth.object_type,
                    predicted_type=pred.object_type,
                    matched=True,
                    confidence=pred.confidence,
                )
            )
        else:
            object_matches.append(
                PerceptionMatch(
                    truth_object_id=truth.object_id,
                    predicted_object_id=None,
                    truth_type=truth.object_type,
                    predicted_type=None,
                    matched=False,
                    confidence=None,
                )
            )

    for i, item in enumerate(projected_detections):
        if i in used_idx:
            continue
        pred = item.original
        object_matches.append(
            PerceptionMatch(
                truth_object_id=None,
                predicted_object_id=str(pred.object_id),
                truth_type=None,
                predicted_type=pred.object_type,
                matched=False,
                confidence=pred.confidence,
            )
        )

    matched_count = sum(1 for m in object_matches if m.matched)
    prec, rec = _precision_recall(matched_count, truth_count, predicted_count)
    return PerceptionEvalResult(
        backend_name=backend_name,
        truth_count=truth_count,
        predicted_count=predicted_count,
        matched_count=matched_count,
        unmatched_truth_count=truth_count - matched_count,
        unmatched_prediction_count=predicted_count - matched_count,
        object_matches=object_matches,
        message=PROJECTED_EVAL_NOTE,
        precision=prec,
        recall=rec,
    )
