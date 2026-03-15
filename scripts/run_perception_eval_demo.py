"""
Run perception evaluation: compare simulator truth with metadata and optional YOLO outputs.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.agents.perception_agent import perceive_from_objects, perceive_image, get_yolo_backend_status
from backend.schemas.perception import PerceptionRequest
from backend.services.perception_eval_service import (
    evaluate_perception,
    truth_objects_from_world,
)
from backend.simulator.camera import default_camera_config
from backend.simulator.environment import SimulationEnvironment


def main() -> None:
    env = SimulationEnvironment(use_gui=False)
    try:
        target = env.get_target_object()
        obstacles = env.get_obstacle_objects()
        truth = truth_objects_from_world(target, obstacles)
        print(f"Truth objects: {len(truth)} (1 target + {len(obstacles)} obstacles)")

        result_meta = perceive_from_objects(obstacles, target, PerceptionRequest())
        eval_meta = evaluate_perception(
            truth,
            result_meta.detected_targets,
            result_meta.detected_obstacles,
            backend_name="metadata",
        )
        print(f"\n[metadata] truth={eval_meta.truth_count} pred={eval_meta.predicted_count} "
              f"matched={eval_meta.matched_count} unmatched_truth={eval_meta.unmatched_truth_count} "
              f"unmatched_pred={eval_meta.unmatched_prediction_count}")
        for m in eval_meta.object_matches:
            print(f"  {m.truth_object_id} {m.truth_type} <-> {m.predicted_object_id} {m.predicted_type} matched={m.matched}")

        if get_yolo_backend_status() == "available":
            config = default_camera_config(width=320, height=240)
            frame = env.capture_frame(config)
            result_yolo = perceive_image(frame.rgb, request=PerceptionRequest())
            eval_yolo = evaluate_perception(
                truth,
                result_yolo.detected_targets,
                result_yolo.detected_obstacles,
                backend_name="yolo",
            )
            print(f"\n[yolo] truth={eval_yolo.truth_count} pred={eval_yolo.predicted_count} "
                  f"matched={eval_yolo.matched_count} | {eval_yolo.message or ''}")
        else:
            print("\n[yolo] skipped (backend unavailable)")
    finally:
        env.shutdown()


if __name__ == "__main__":
    main()
