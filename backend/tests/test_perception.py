"""Perception agent and schema tests."""

import pytest

from backend.agents.perception_agent import perceive
from backend.schemas.perception import (
    DetectedObject,
    PerceptionRequest,
    PerceptionResult,
)


# Default world layout (same as world_builder).
_DEFAULT_OBSTACLE_POSITIONS = [(-3.0, 0.0), (3.0, 0.0), (1.0, 1.0)]
_DEFAULT_OBSTACLE_TYPES = ["wall", "wall", "block"]
_DEFAULT_TARGET = (5.0, 3.0)


def test_target_detected_in_default_world() -> None:
    result = perceive(
        _DEFAULT_OBSTACLE_POSITIONS,
        _DEFAULT_OBSTACLE_TYPES,
        _DEFAULT_TARGET[0],
        _DEFAULT_TARGET[1],
    )
    assert len(result.detected_targets) == 1
    t = result.detected_targets[0]
    assert t.object_type == "target"
    assert t.object_id == "target"
    assert t.x == 5.0
    assert t.y == 3.0
    assert t.confidence == 1.0


def test_at_least_one_obstacle_detected() -> None:
    result = perceive(
        _DEFAULT_OBSTACLE_POSITIONS,
        _DEFAULT_OBSTACLE_TYPES,
        _DEFAULT_TARGET[0],
        _DEFAULT_TARGET[1],
    )
    assert len(result.detected_obstacles) >= 1
    for o in result.detected_obstacles:
        assert o.object_type in ("wall", "block", "obstacle")
        assert 0.0 <= o.confidence <= 1.0


def test_perception_result_schema_stable() -> None:
    result = perceive(
        [(-1.0, 0.0)],
        ["wall"],
        2.0,
        1.0,
        PerceptionRequest(include_obstacles=True, include_targets=True),
    )
    assert isinstance(result, PerceptionResult)
    assert hasattr(result, "detected_targets")
    assert hasattr(result, "detected_obstacles")
    assert hasattr(result, "message")
    assert isinstance(result.detected_targets, list)
    assert isinstance(result.detected_obstacles, list)
    for obj in result.detected_targets + result.detected_obstacles:
        assert isinstance(obj, DetectedObject)
        assert hasattr(obj, "object_id")
        assert hasattr(obj, "object_type")
        assert hasattr(obj, "x")
        assert hasattr(obj, "y")
        assert hasattr(obj, "confidence")


def test_perception_request_filters() -> None:
    result = perceive(
        _DEFAULT_OBSTACLE_POSITIONS,
        _DEFAULT_OBSTACLE_TYPES,
        _DEFAULT_TARGET[0],
        _DEFAULT_TARGET[1],
        PerceptionRequest(include_targets=False, include_obstacles=True),
    )
    assert len(result.detected_targets) == 0
    assert len(result.detected_obstacles) == 3

    result2 = perceive(
        _DEFAULT_OBSTACLE_POSITIONS,
        _DEFAULT_OBSTACLE_TYPES,
        _DEFAULT_TARGET[0],
        _DEFAULT_TARGET[1],
        PerceptionRequest(include_targets=True, include_obstacles=False),
    )
    assert len(result2.detected_targets) == 1
    assert len(result2.detected_obstacles) == 0
