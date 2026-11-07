"""
Run camera demo: init sim, capture frame(s), print shape/metadata, optionally save PNG.
Optional: run YOLO perception on captured frame if ultralytics available.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.schemas.camera import CapturedFrame
from backend.simulator.camera import default_camera_config
from backend.simulator.environment import SimulationEnvironment

OUTPUT_PNG = "camera_capture.png"


def save_frame_png(frame: CapturedFrame, path: str) -> None:
    try:
        from PIL import Image

        img = Image.fromarray(frame.rgb)
        img.save(path)
        print(f"Saved: {Path(path).resolve()}")
    except ImportError:
        print("PIL not available; skip save.")


def main() -> None:
    env = SimulationEnvironment(use_gui=False)
    try:
        config = default_camera_config(width=320, height=240)
        frame = env.capture_frame(config)
        print(f"Frame shape: {frame.rgb.shape}")
        p = frame.camera_pose
        print(
            f"Camera pose: pos=({p.position_x:.4f}, {p.position_y:.4f}, {p.position_z:.4f}) "
            f"yaw={p.yaw} pitch={p.pitch} roll={p.roll}"
        )
        i = frame.camera_intrinsics
        print(
            f"Camera intrinsics: {i.width}x{i.height} fov={i.fov} "
            f"near={i.near_plane} far={i.far_plane}"
        )
        print(f"Timestamp: {frame.timestamp}")
        save_frame_png(frame, OUTPUT_PNG)

        try:
            from backend.agents.perception_agent import perceive_image

            result = perceive_image(frame.rgb)
            print(f"YOLO on captured frame: targets={len(result.detected_targets)}, obstacles={len(result.detected_obstacles)}")
            if result.message:
                print(f"  Message: {result.message}")
        except Exception as e:
            print(f"YOLO path skipped: {e}")
    finally:
        env.shutdown()


if __name__ == "__main__":
    main()
