"""Simulator lifecycle and waypoint execution. Owns env create, executor run, shutdown, result packaging."""

from typing import List, Optional, Tuple

from backend.schemas.execution import ExecutionResult
from backend.schemas.navigation import Waypoint
from backend.services.telemetry_service import TelemetryService
from backend.simulator.execution_engine import WaypointExecutor
from backend.simulator.environment import SimulationEnvironment


def run_sim_execution(
    mission_id: str,
    waypoints: List[Waypoint],
    telemetry_service: TelemetryService,
    use_gui: bool = False,
    robot_start: Optional[Tuple[float, float, float]] = None,
) -> ExecutionResult:
    """Create sim, run WaypointExecutor, shutdown, return result. Raises on env create failure."""
    env = SimulationEnvironment(use_gui=use_gui, robot_start=robot_start)
    try:
        executor = WaypointExecutor(env, mission_id, telemetry_service)
        return executor.execute(waypoints)
    finally:
        env.shutdown()
