"""Run perception demo: init sim, run perception agent, print detections, shutdown."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.agents.perception_agent import perceive_from_objects
from backend.schemas.perception import PerceptionRequest
from backend.simulator.environment import SimulationEnvironment


def main() -> None:
    env = SimulationEnvironment(use_gui=False)
    try:
        obstacle_objects = env.get_obstacle_objects()
        target_object = env.get_target_object()
        result = perceive_from_objects(
            obstacle_objects,
            target_object,
            PerceptionRequest(),
        )
        print("Detected targets:", [(t.object_id, t.object_type, t.x, t.y) for t in result.detected_targets])
        print("Detected obstacles:", [(o.object_id, o.object_type, o.x, o.y) for o in result.detected_obstacles])
    finally:
        env.shutdown()


if __name__ == "__main__":
    main()
