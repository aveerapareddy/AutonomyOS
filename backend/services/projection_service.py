"""Approximate image-space to world-space projection utilities."""

import math
from typing import Sequence

from backend.schemas.camera import CameraIntrinsics, CameraPose, CapturedFrame
from backend.schemas.perception import DetectedObject
from backend.schemas.projection import ProjectedDetection, ProjectionInput, ProjectionOutput

DEFAULT_WORLD_BOUNDS = (-10.0, 10.0, -10.0, 10.0)
GROUND_Z = 0.0


def _half_extents_from_camera(
    camera_pose: CameraPose,
    camera_intrinsics: CameraIntrinsics,
    world_bounds: tuple[float, float, float, float],
) -> tuple[float, float]:
    min_x, max_x, min_y, max_y = world_bounds
    half_bound_x = max((max_x - min_x) * 0.5, 1e-6)
    half_bound_y = max((max_y - min_y) * 0.5, 1e-6)

    height = max(camera_pose.position_z, 1e-6)
    fov_rad = math.radians(camera_intrinsics.fov)
    half_span_y = height * math.tan(fov_rad * 0.5)
    aspect = camera_intrinsics.width / max(camera_intrinsics.height, 1)
    half_span_x = half_span_y * aspect

    return (
        min(half_span_x, half_bound_x),
        min(half_span_y, half_bound_y),
    )


def project_to_world(
    detection: ProjectionInput,
    camera_pose: CameraPose,
    camera_intrinsics: CameraIntrinsics,
    world_bounds: tuple[float, float, float, float] = DEFAULT_WORLD_BOUNDS,
) -> ProjectionOutput:
    """
    Deterministic approximate mapping:
    - image center (0.5, 0.5) -> world center (0, 0)
    - linear scaling to camera-dependent spans clamped by world bounds
    """
    min_x, max_x, min_y, max_y = world_bounds
    if min_x >= max_x or min_y >= max_y:
        return ProjectionOutput(
            world_x=0.0,
            world_y=0.0,
            world_z=None,
            valid=False,
            message="Invalid world bounds",
        )

    half_x, half_y = _half_extents_from_camera(camera_pose, camera_intrinsics, world_bounds)
    world_x = (detection.image_x - 0.5) * (2.0 * half_x)
    world_y = (0.5 - detection.image_y) * (2.0 * half_y)
    world_x = max(min(world_x, max_x), min_x)
    world_y = max(min(world_y, max_y), min_y)

    return ProjectionOutput(
        world_x=world_x,
        world_y=world_y,
        world_z=GROUND_Z,
        valid=True,
        message=None,
    )


def project_detections(
    detected_objects: Sequence[DetectedObject],
    frame: CapturedFrame,
    world_bounds: tuple[float, float, float, float] = DEFAULT_WORLD_BOUNDS,
    default_depth: float = 1.0,
) -> list[ProjectedDetection]:
    """Project all detections from normalized image space into approximate world space."""
    projected: list[ProjectedDetection] = []
    for det in detected_objects:
        projection_input = ProjectionInput(
            image_x=det.x,
            image_y=det.y,
            depth=default_depth,
        )
        out = project_to_world(
            detection=projection_input,
            camera_pose=frame.camera_pose,
            camera_intrinsics=frame.camera_intrinsics,
            world_bounds=world_bounds,
        )
        projected.append(ProjectedDetection(original=det, projection=out))
    return projected
