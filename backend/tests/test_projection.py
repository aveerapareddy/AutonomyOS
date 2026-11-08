"""Projection service tests."""

from backend.schemas.camera import CameraIntrinsics, CameraPose, CapturedFrame
from backend.schemas.perception import DetectedObject
from backend.schemas.projection import ProjectionInput
from backend.services.projection_service import (
    DEFAULT_WORLD_BOUNDS,
    project_detections,
    project_to_world,
)


def _sample_pose() -> CameraPose:
    return CameraPose(
        position_x=0.0,
        position_y=0.0,
        position_z=20.0,
        yaw=0.0,
        pitch=-60.0,
        roll=0.0,
    )


def _sample_intrinsics() -> CameraIntrinsics:
    return CameraIntrinsics(
        width=320,
        height=240,
        fov=60.0,
        near_plane=0.1,
        far_plane=500.0,
    )


def test_projection_returns_valid_output() -> None:
    out = project_to_world(ProjectionInput(image_x=0.6, image_y=0.4), _sample_pose(), _sample_intrinsics())
    assert out.valid is True
    assert out.world_z == 0.0


def test_center_maps_near_world_center() -> None:
    out = project_to_world(ProjectionInput(image_x=0.5, image_y=0.5), _sample_pose(), _sample_intrinsics())
    assert abs(out.world_x) < 1e-6
    assert abs(out.world_y) < 1e-6


def test_corners_map_to_expected_bounds() -> None:
    min_x, max_x, min_y, max_y = DEFAULT_WORLD_BOUNDS
    top_left = project_to_world(ProjectionInput(image_x=0.0, image_y=0.0), _sample_pose(), _sample_intrinsics())
    bottom_right = project_to_world(ProjectionInput(image_x=1.0, image_y=1.0), _sample_pose(), _sample_intrinsics())
    assert top_left.world_x <= min_x + 1e-6
    assert top_left.world_y >= max_y - 1e-6
    assert bottom_right.world_x >= max_x - 1e-6
    assert bottom_right.world_y <= min_y + 1e-6


def test_empty_detections_handled() -> None:
    frame = CapturedFrame(
        rgb=None,
        width=320,
        height=240,
        camera_pose=_sample_pose(),
        camera_intrinsics=_sample_intrinsics(),
        timestamp=1.0,
    )
    projected = project_detections([], frame)
    assert projected == []


def test_project_detections_returns_outputs() -> None:
    frame = CapturedFrame(
        rgb=None,
        width=320,
        height=240,
        camera_pose=_sample_pose(),
        camera_intrinsics=_sample_intrinsics(),
        timestamp=1.0,
    )
    detections = [DetectedObject(object_id="d0", object_type="obstacle", x=0.5, y=0.5, confidence=0.8)]
    projected = project_detections(detections, frame)
    assert len(projected) == 1
    assert projected[0].original.object_id == "d0"
    assert projected[0].projection.valid is True
