"""Run full mission: create mission, execute (plan + perceive + navigate + waypoint execution), print summary."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.api.dependencies import get_mission_orchestrator, get_orchestrator_service
from backend.schemas.mission import MissionRequest


def main() -> None:
    orchestrator_create = get_mission_orchestrator()
    response = orchestrator_create.create(MissionRequest(mission_text="Go to the red cube", world_id="w1"))
    mission_id = response.mission_id
    print("Created mission:", mission_id)

    orchestrator_exec = get_orchestrator_service()
    summary = orchestrator_exec.execute(mission_id)
    if summary is None:
        print("Mission not found")
        return

    print("Status:", summary.status)
    print("Path found:", summary.path_found)
    print("Waypoint count:", summary.waypoint_count)
    print("Execution status:", summary.execution_status)
    if summary.final_robot_position:
        print("Final robot position:", summary.final_robot_position)
    if summary.execution_steps:
        print("Execution steps:", len(summary.execution_steps), "waypoints reached")
    if summary.message:
        print("Message:", summary.message)


if __name__ == "__main__":
    main()
