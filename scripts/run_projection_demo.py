"""Capture frame, run image detections, and project to approximate world coordinates."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.agents.perception_agent import get_yolo_backend_status, perceive_image
from backend.schemas.perception import DetectedObject, PerceptionRequest
from backend.services.projection_service import project_detections
from backend.simulator.camera import default_camera_config
from backend.simulator.environment import SimulationEnvironment
from backend.simulator.world_builder import WORLD_BOUNDS


def _mock_detections() -> list[DetectedObject]:
    return [
        DetectedObject(object_id="mock_center", object_type="target_candidate", x=0.5, y=0.5, confidence=0.9),
        DetectedObject(object_id="mock_tl", object_type="obstacle", x=0.1, y=0.1, confidence=0.8),
        DetectedObject(object_id="mock_br", object_type="obstacle", x=0.9, y=0.9, confidence=0.8),
    ]


def main() -> None:
    env = SimulationEnvironment(use_gui=False)
    try:
        frame = env.capture_frame(default_camera_config(width=320, height=240))
        print(f"Frame: {frame.width}x{frame.height}")
        print(f"Camera z: {frame.camera_pose.position_z:.4f}")
        print(f"World bounds: {WORLD_BOUNDS}")

        detections: list[DetectedObject]
        status = get_yolo_backend_status()
        if status == "available":
            result = perceive_image(frame.rgb, request=PerceptionRequest())
            detections = list(result.detected_targets) + list(result.detected_obstacles)
            print(f"YOLO backend: available, detections={len(detections)}")
            if result.message:
                print(f"YOLO message: {result.message}")
        else:
            detections = _mock_detections()
            print("YOLO backend: unavailable, using mock detections")

        projected = project_detections(detections, frame=frame, world_bounds=WORLD_BOUNDS)
        if not projected:
            print("No detections to project.")
            return

        for item in projected:
            p = item.projection
            print(
                f"{item.original.object_id} {item.original.object_type} "
                f"img=({item.original.x:.3f},{item.original.y:.3f}) "
                f"-> world=({p.world_x:.3f},{p.world_y:.3f},{p.world_z}) valid={p.valid}"
            )
    finally:
        env.shutdown()


if __name__ == "__main__":
    main()
