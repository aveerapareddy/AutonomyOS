"""Target selection from MissionPlan labels."""

from backend.schemas.perception import DetectedObject
from backend.services.target_selection import select_navigation_goal


def test_default_label_uses_first_target() -> None:
    targets = [
        DetectedObject(object_id="target", object_type="target", x=5.0, y=3.0, confidence=1.0),
    ]
    obs = [
        DetectedObject(object_id="obstacle_2", object_type="block", x=1.0, y=1.0, confidence=1.0),
    ]
    sel, err = select_navigation_goal(targets, obs, "target")
    assert err is None
    assert sel is not None and sel.object_id == "target"


def test_red_cube_label_matches_target_type() -> None:
    targets = [
        DetectedObject(object_id="target", object_type="target", x=5.0, y=3.0, confidence=1.0),
    ]
    sel, err = select_navigation_goal(targets, [], "red cube")
    assert err is None
    assert sel.object_type == "target"


def test_block_label_selects_obstacle() -> None:
    targets = [
        DetectedObject(object_id="target", object_type="target", x=5.0, y=3.0, confidence=1.0),
    ]
    obs = [
        DetectedObject(object_id="obstacle_2", object_type="block", x=1.0, y=1.0, confidence=1.0),
    ]
    sel, err = select_navigation_goal(targets, obs, "block")
    assert err is None
    assert sel is not None and sel.object_type == "block"


def test_unknown_label_fails_cleanly() -> None:
    targets = [
        DetectedObject(object_id="target", object_type="target", x=5.0, y=3.0, confidence=1.0),
    ]
    sel, err = select_navigation_goal(targets, [], "blue crate xyz")
    assert sel is None
    assert err is not None and "no_detection_matches" in err
