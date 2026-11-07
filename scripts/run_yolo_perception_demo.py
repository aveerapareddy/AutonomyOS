"""Run YOLO perception backend on an image; print PerceptionResult. No GUI."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from backend.agents.perception_agent import perceive_image, get_yolo_backend_status
from backend.schemas.perception import PerceptionRequest


def main() -> None:
    status = get_yolo_backend_status()
    print(f"YOLO backend: {status}")

    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        print(f"Image: {image_path}")
        result = perceive_image(image_path, request=PerceptionRequest())
    else:
        print("No image path given; using synthetic 640x480 RGB (may yield no detections).")
        synthetic = np.zeros((480, 640, 3), dtype=np.uint8)
        synthetic[:] = (240, 230, 220)
        result = perceive_image(synthetic, request=PerceptionRequest())

    if result.message:
        print("Message:", result.message)
    print("Detected targets:", len(result.detected_targets))
    for t in result.detected_targets:
        print(f"  {t.object_id} {t.object_type} x={t.x:.4f} y={t.y:.4f} conf={t.confidence:.4f}")
    print("Detected obstacles:", len(result.detected_obstacles))
    for o in result.detected_obstacles[:10]:
        print(f"  {o.object_id} {o.object_type} x={o.x:.4f} y={o.y:.4f} conf={o.confidence:.4f}")
    if len(result.detected_obstacles) > 10:
        print(f"  ... and {len(result.detected_obstacles) - 10} more")


if __name__ == "__main__":
    main()
