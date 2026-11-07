"""
Run perception evaluation: metadata vs truth; projected image detections vs truth.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.agents.perception_agent import get_yolo_backend_status, perceive_from_objects, perceive_image
from backend.schemas.perception import DetectedObject, PerceptionRequest
from backend.services.perception_eval_service import (
    evaluate_perception,
    evaluate_projected_detections,
    truth_objects_from_world,
)
from backend.services.projection_service import project_detections
from backend.simulator.camera import default_camera_config
from backend.simulator.environment import SimulationEnvironment


def _mock_image_detections() -> list[DetectedObject]:
    return [
        DetectedObject(object_id="mock_0", object_type="target_candidate", x=0.5, y=0.5, confidence=0.85),
        DetectedObject(object_id="mock_1", object_type="person", x=0.2, y=0.4, confidence=0.7),
    ]


def main() -> None:
    env = SimulationEnvironment(use_gui=False)
    try:
        target = env.get_target_object()
        obstacles = env.get_obstacle_objects()
        truth = truth_objects_from_world(target, obstacles)
        bounds = env.get_world_bounds()
        print(f"Truth objects: {len(truth)} (1 target + {len(obstacles)} obstacles)")
        print(f"World bounds: {bounds}")

        result_meta = perceive_from_objects(obstacles, target, PerceptionRequest())
        eval_meta = evaluate_perception(
            truth,
            result_meta.detected_targets,
            result_meta.detected_obstacles,
            backend_name="metadata",
        )
        print(
            f"\n[metadata] truth={eval_meta.truth_count} pred={eval_meta.predicted_count} "
            f"matched={eval_meta.matched_count} precision={eval_meta.precision} recall={eval_meta.recall}"
        )
        for m in eval_meta.object_matches:
            print(f"  {m.truth_object_id} {m.truth_type} <-> {m.predicted_object_id} {m.predicted_type} matched={m.matched}")

        config = default_camera_config(width=320, height=240)
        frame = env.capture_frame(config)
        if get_yolo_backend_status() == "available":
            result_img = perceive_image(frame.rgb, request=PerceptionRequest())
            dets = list(result_img.detected_targets) + list(result_img.detected_obstacles)
            print(f"\n[yolo] detections={len(dets)}")
            if result_img.message:
                print(f"  note: {result_img.message}")
        else:
            dets = _mock_image_detections()
            print(f"\n[yolo] backend unavailable; using {len(dets)} mock image-space detections")

        projected = project_detections(dets, frame=frame, world_bounds=bounds)
        eval_proj = evaluate_projected_detections(truth, projected)
        print(
            f"\n[projected] backend={eval_proj.backend_name} truth={eval_proj.truth_count} "
            f"pred={eval_proj.predicted_count} matched={eval_proj.matched_count} "
            f"precision={eval_proj.precision} recall={eval_proj.recall}"
        )
        if eval_proj.message:
            print(f"  {eval_proj.message}")
        for m in eval_proj.object_matches:
            print(f"  {m.truth_object_id} {m.truth_type} <-> {m.predicted_object_id} {m.predicted_type} matched={m.matched}")
    finally:
        env.shutdown()


if __name__ == "__main__":
    main()
