"""Run benchmarks over a list of scenario configs; collect per-scenario and aggregate metrics."""

from typing import List, Tuple

from backend.schemas.benchmark import BenchmarkSummary, ScenarioBenchmarkResult
from backend.schemas.execution import MissionExecutionSummary
from backend.schemas.mission import MissionRequest
from backend.schemas.world import WorldObject
from backend.scenarios.scenario_config import ScenarioConfig
from backend.services.mission_service import MissionService
from backend.services.orchestrator_service import OrchestratorService
from backend.services.telemetry_service import TelemetryService


def _layout_from_scenario(
    scenario: ScenarioConfig,
) -> Tuple[Tuple[float, float, float, float], List[WorldObject], WorldObject]:
    """Convert scenario config to (world_bounds, obstacle_objects, target_object)."""
    obstacle_objects = [
        WorldObject(
            object_id=f"obstacle_{i}",
            object_type=typ,
            x=pos[0],
            y=pos[1],
        )
        for i, (pos, typ) in enumerate(
            zip(scenario.obstacle_positions, scenario.obstacle_types)
        )
    ]
    if len(scenario.obstacle_positions) > len(scenario.obstacle_types):
        for i in range(len(scenario.obstacle_types), len(scenario.obstacle_positions)):
            pos = scenario.obstacle_positions[i]
            obstacle_objects.append(
                WorldObject(object_id=f"obstacle_{i}", object_type="obstacle", x=pos[0], y=pos[1])
            )
    target_object = WorldObject(
        object_id="target",
        object_type="target",
        x=scenario.target_position[0],
        y=scenario.target_position[1],
    )
    return scenario.world_bounds, obstacle_objects, target_object


def run_benchmark(
    scenario_configs: List[ScenarioConfig],
    mission_service: MissionService,
    telemetry_service: TelemetryService,
    benchmark_id: str,
    benchmark_name: str,
) -> BenchmarkSummary:
    """Run full pipeline for each scenario; return aggregate and per-scenario results."""
    results: List[ScenarioBenchmarkResult] = []
    waypoint_counts: List[int] = []
    execution_step_counts: List[int] = []

    for scenario in scenario_configs:
        layout_provider = lambda s=scenario: _layout_from_scenario(s)
        mission_resp = mission_service.create(
            MissionRequest(mission_text="Go to target", world_id=scenario.scenario_id)
        )
        def get_robot_start() -> Tuple[float, float, float]:
            return scenario.robot_start_position

        orchestrator = OrchestratorService(
            mission_service=mission_service,
            telemetry_service=telemetry_service,
            world_layout_provider=layout_provider,
            robot_start_provider=get_robot_start,
        )
        summary = orchestrator.execute(mission_resp.mission_id)

        if summary is None:
            results.append(
                ScenarioBenchmarkResult(
                    scenario_id=scenario.scenario_id,
                    scenario_name=scenario.scenario_name,
                    robot_start_position=scenario.robot_start_position,
                    target_position=scenario.target_position,
                    success=False,
                    path_found=False,
                    message="Mission not found",
                )
            )
            continue

        path_found = summary.path_found
        waypoint_count = summary.waypoint_count
        path_length_raw = getattr(summary, "path_length_raw", None)
        execution_steps = len(summary.execution_steps) if summary.execution_steps else 0
        success = summary.status == "completed"

        results.append(
            ScenarioBenchmarkResult(
                scenario_id=scenario.scenario_id,
                scenario_name=scenario.scenario_name,
                robot_start_position=scenario.robot_start_position,
                target_position=scenario.target_position,
                success=success,
                path_found=path_found,
                waypoint_count=waypoint_count,
                path_length_raw=path_length_raw,
                execution_steps=execution_steps,
                message=summary.message,
            )
        )
        if success:
            waypoint_counts.append(waypoint_count)
            execution_step_counts.append(execution_steps)

    total = len(results)
    success_count = sum(1 for r in results if r.success)
    failure_count = total - success_count
    success_rate = success_count / total if total else 0.0
    avg_waypoints = sum(waypoint_counts) / len(waypoint_counts) if waypoint_counts else 0.0
    avg_steps = sum(execution_step_counts) / len(execution_step_counts) if execution_step_counts else 0.0

    return BenchmarkSummary(
        benchmark_id=benchmark_id,
        benchmark_name=benchmark_name,
        total_scenarios=total,
        success_count=success_count,
        failure_count=failure_count,
        success_rate=round(success_rate, 4),
        average_waypoint_count=round(avg_waypoints, 2),
        average_execution_steps=round(avg_steps, 2),
        scenario_results=results,
    )
