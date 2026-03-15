"""Perception evaluation service tests."""

from backend.schemas.perception import DetectedObject
from backend.schemas.perception_eval import PerceptionEvalResult
from backend.schemas.world import WorldObject
from backend.services.perception_eval_service import (
    evaluate_perception,
    truth_objects_from_world,
)


def test_truth_objects_from_world() -> None:
    target = WorldObject(object_id="target", object_type="target", x=5.0, y=3.0)
    obstacles = [
        WorldObject(object_id="o0", object_type="wall", x=-3.0, y=0.0),
        WorldObject(object_id="o1", object_type="block", x=1.0, y=1.0),
    ]
    truth = truth_objects_from_world(target, obstacles)
    assert len(truth) == 3
    assert truth[0].object_id == "target"
    assert truth[1].object_id == "o0"
    assert truth[2].object_id == "o1"


def test_evaluate_empty_predictions() -> None:
    target = WorldObject(object_id="target", object_type="target", x=5.0, y=3.0)
    truth = truth_objects_from_world(target, [])
    result = evaluate_perception(truth, [], [], backend_name="metadata")
    assert result.truth_count == 1
    assert result.predicted_count == 0
    assert result.matched_count == 0
    assert result.unmatched_truth_count == 1
    assert result.unmatched_prediction_count == 0
    assert len(result.object_matches) == 1
    assert result.object_matches[0].matched is False


def test_evaluate_empty_truth() -> None:
    preds = [
        DetectedObject(object_id="p0", object_type="target", x=5.0, y=3.0, confidence=1.0),
    ]
    result = evaluate_perception([], preds, [], backend_name="metadata")
    assert result.truth_count == 0
    assert result.predicted_count == 1
    assert result.matched_count == 0
    assert result.unmatched_prediction_count == 1


def test_metadata_backend_high_match_on_default_world() -> None:
    target = WorldObject(object_id="target", object_type="target", x=5.0, y=3.0)
    obstacles = [
        WorldObject(object_id="obstacle_0", object_type="wall", x=-3.0, y=0.0),
        WorldObject(object_id="obstacle_1", object_type="wall", x=3.0, y=0.0),
        WorldObject(object_id="obstacle_2", object_type="block", x=1.0, y=1.0),
    ]
    truth = truth_objects_from_world(target, obstacles)
    detected_targets = [
        DetectedObject(object_id="target", object_type="target", x=5.0, y=3.0, confidence=1.0),
    ]
    detected_obstacles = [
        DetectedObject(object_id="obstacle_0", object_type="wall", x=-3.0, y=0.0, confidence=1.0),
        DetectedObject(object_id="obstacle_1", object_type="wall", x=3.0, y=0.0, confidence=1.0),
        DetectedObject(object_id="obstacle_2", object_type="block", x=1.0, y=1.0, confidence=1.0),
    ]
    result = evaluate_perception(
        truth,
        detected_targets,
        detected_obstacles,
        backend_name="metadata",
        position_tolerance=0.6,
    )
    assert result.matched_count == 4
    assert result.unmatched_truth_count == 0
    assert result.unmatched_prediction_count == 0
    assert result.message is None


def test_yolo_backend_returns_message_no_position_matching() -> None:
    target = WorldObject(object_id="target", object_type="target", x=5.0, y=3.0)
    truth = truth_objects_from_world(target, [])
    preds = [
        DetectedObject(object_id="det_0", object_type="person", x=0.5, y=0.3, confidence=0.9),
    ]
    result = evaluate_perception(truth, [], preds, backend_name="yolo")
    assert result.backend_name == "yolo"
    assert result.matched_count == 0
    assert result.message is not None
    assert "image-space" in result.message
    assert len(result.object_matches) == 0
