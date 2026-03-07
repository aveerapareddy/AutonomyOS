"""Run navigation demo: build grid from sim world, plan path, print result."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.agents.navigation_agent import plan_path
from backend.simulator.environment import SimulationEnvironment
from backend.simulator.grid_map import build_occupancy_grid


def main() -> None:
    env = SimulationEnvironment(use_gui=False)
    try:
        robot = env.get_robot_pose()
        target = env.get_target_pose()
        bounds = env.get_world_bounds()
        obstacles = env.get_obstacles()

        grid = build_occupancy_grid(bounds, obstacles)
        result = plan_path(
            grid,
            robot.x,
            robot.y,
            target.x,
            target.y,
        )

        print("Start pose:", (robot.x, robot.y))
        print("Target pose:", (target.x, target.y, target.z))
        print("Path found:", result.path_found)
        if result.message:
            print("Message:", result.message)
        print("Path length:", result.path_length)
        print("Waypoints:", [(w.x, w.y) for w in result.waypoints])
    finally:
        env.shutdown()


if __name__ == "__main__":
    main()
