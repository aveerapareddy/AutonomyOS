"""Perception evaluation service tests."""

from backend.schemas.perception import DetectedObject
from backend.schemas.projection import ProjectedDetection, ProjectionOutput
from backend.schemas.world import WorldObject
from backend.services.perception_eval_service import (
    evaluate_perception,
    evaluate_projected_detections,
    predicted_semantic_family,
    truth_semantic_family,
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


def test_semantic_families() -> None:
    assert truth_semantic_family("target") == "target"
    assert truth_semantic_family("wall") == "obstacle"
    assert predicted_semantic_family("target_candidate") == "target"
    assert predicted_semantic_family("person") == "obstacle"


def test_evaluate_empty_predictions() -> None:
    target = WorldObject(object_id="target", object_type="target", x=5.0, y=3.0)
    truth = truth_objects_from_world(target, [])
    result = evaluate_perception(truth, [], [], backend_name="metadata")
    assert result.truth_count == 1
    assert result.predicted_count == 0
    assert result.matched_count == 0
    assert result.unmatched_truth_count == 1
    assert result.unmatched_prediction_count == 0
    assert result.precision is None
    assert result.recall == 0.0
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
    assert result.recall is None


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
    assert result.precision == 1.0
    assert result.recall == 1.0


def test_projected_center_matches_truth_at_origin() -> None:
    truth = [WorldObject(object_id="target", object_type="target", x=0.0, y=0.0)]
    projected = [
        ProjectedDetection(
            original=DetectedObject(
                object_id="det0",
                object_type="target_candidate",
                x=0.5,
                y=0.5,
                confidence=0.9,
            ),
            projection=ProjectionOutput(
                world_x=0.0,
                world_y=0.0,
                world_z=0.0,
                valid=True,
            ),
        )
    ]
    result = evaluate_projected_detections(truth, projected, position_tolerance=0.5)
    assert result.matched_count == 1
    assert result.precision == 1.0
    assert result.recall == 1.0
    assert result.backend_name == "yolo_projected"


def test_projected_empty_list() -> None:
    truth = [WorldObject(object_id="target", object_type="target", x=0.0, y=0.0)]
    result = evaluate_projected_detections(truth, [])
    assert result.predicted_count == 0
    assert result.matched_count == 0
    assert result.unmatched_truth_count == 1
    assert result.precision is None
    assert result.recall == 0.0


def test_projected_invalid_projection_skipped_for_match() -> None:
    truth = [WorldObject(object_id="target", object_type="target", x=0.0, y=0.0)]
    projected = [
        ProjectedDetection(
            original=DetectedObject(object_id="d0", object_type="target_candidate", x=0.5, y=0.5, confidence=0.9),
            projection=ProjectionOutput(world_x=0.0, world_y=0.0, world_z=None, valid=False, message="bad"),
        )
    ]
    result = evaluate_projected_detections(truth, projected)
    assert result.matched_count == 0
