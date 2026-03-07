"""Run a short simulation demo: init, hardcoded movements, print poses, shutdown."""

import sys
from pathlib import Path

# Allow importing backend when run as script from repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.simulator.actions import RobotAction
from backend.simulator.environment import SimulationEnvironment


def main() -> None:
    env = SimulationEnvironment(use_gui=False)
    try:
        print("Robot start:", env.get_robot_pose().as_tuple())
        print("Target:", env.get_target_pose().as_tuple())

        steps = [
            (RobotAction.FORWARD, 60),
            (RobotAction.TURN_LEFT, 40),
            (RobotAction.FORWARD, 40),
            (RobotAction.TURN_RIGHT, 20),
            (RobotAction.FORWARD, 30),
        ]
        for action, count in steps:
            for _ in range(count):
                env.step(action)
            print(f"After {action.value} x{count}: {env.get_robot_pose().as_tuple()}")

    finally:
        env.shutdown()
    print("Done.")


if __name__ == "__main__":
    main()
