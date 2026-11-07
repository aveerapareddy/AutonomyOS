"""Select a navigation goal from perception output using planned target_label."""

from typing import List, Optional, Sequence, Tuple

from backend.schemas.perception import DetectedObject


def _norm(label: Optional[str]) -> str:
    return (label or "").strip().lower()


def _matches_detection(label_norm: str, det: DetectedObject) -> bool:
    ot = det.object_type.lower()
    oid = str(det.object_id).lower()
    if not label_norm:
        return True
    if label_norm == ot or label_norm == oid:
        return True
    if ot == "target" and ("red" in label_norm or "cube" in label_norm or label_norm in ("goal",)):
        return True
    if ot in ("wall", "block"):
        if ot in label_norm:
            return True
        if ot == "block" and "block" in label_norm:
            return True
    return False


def select_navigation_goal(
    detected_targets: Sequence[DetectedObject],
    detected_obstacles: Sequence[DetectedObject],
    target_label: Optional[str],
) -> Tuple[Optional[DetectedObject], Optional[str]]:
    label_norm = _norm(target_label)
    if not detected_targets and not detected_obstacles:
        return None, "no_targets_detected"

    if not label_norm or label_norm in ("target", "default", "goal"):
        if not detected_targets:
            return None, "no_targets_detected"
        return detected_targets[0], None

    candidates: List[DetectedObject] = list(detected_targets)
    if _label_suggests_obstacle(label_norm):
        candidates = list(detected_obstacles) + candidates

    matched = [d for d in candidates if _matches_detection(label_norm, d)]
    if not matched:
        return None, f"no_detection_matches_planned_target:{target_label!r}"
    return matched[0], None


def _label_suggests_obstacle(label_norm: str) -> bool:
    keys = ("wall", "block", "obstacle", "barrier")
    if label_norm in keys:
        return True
    return any(k in label_norm for k in keys) and "red" not in label_norm
