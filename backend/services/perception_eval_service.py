"""Perception evaluation: compare simulator truth with perception outputs."""

from typing import List

from backend.schemas.perception import DetectedObject
from backend.schemas.perception_eval import PerceptionEvalResult, PerceptionMatch
from backend.schemas.world import WorldObject

POSITION_TOLERANCE_DEFAULT = 0.5


def truth_objects_from_world(
    target_object: WorldObject,
    obstacle_objects: List[WorldObject],
) -> List[WorldObject]:
    """Extract truth list: target first, then obstacles. Stable IDs and types."""
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
    """
    Compare truth objects to perception output. Metadata backend: match by type and position.
    YOLO backend: predictions are image-space; no position matching, message set.
    """
    predicted = _flatten_predictions(detected_targets, detected_obstacles)
    truth_count = len(truth_objects)
    predicted_count = len(predicted)

    if backend_name == "yolo":
        return PerceptionEvalResult(
            backend_name="yolo",
            truth_count=truth_count,
            predicted_count=predicted_count,
            matched_count=0,
            unmatched_truth_count=truth_count,
            unmatched_prediction_count=predicted_count,
            object_matches=[],
            message="YOLO detections in image-space; no position matching to world truth",
        )

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
    return PerceptionEvalResult(
        backend_name=backend_name,
        truth_count=truth_count,
        predicted_count=predicted_count,
        matched_count=matched_count,
        unmatched_truth_count=truth_count - matched_count,
        unmatched_prediction_count=predicted_count - matched_count,
        object_matches=object_matches,
        message=None,
    )
