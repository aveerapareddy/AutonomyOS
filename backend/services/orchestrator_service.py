"""End-to-end orchestration: plan, perceive, navigate, telemetry."""

from typing import Callable, List, Optional, Tuple

from backend.agents.navigation_agent import plan_path
from backend.agents.perception_agent import perceive_from_objects
from backend.core.constants import (
    TELEMETRY_SOURCE_NAVIGATION_AGENT,
    TELEMETRY_SOURCE_ORCHESTRATOR_SERVICE,
    TELEMETRY_SOURCE_PERCEPTION_AGENT,
    TELEMETRY_SOURCE_PLANNER,
)
from backend.schemas.execution import MissionExecutionSummary
from backend.schemas.telemetry import TelemetryEventType
from backend.schemas.world import WorldObject
from backend.services.execution_service import run_sim_execution
from backend.services.mission_service import MissionService
from backend.services.telemetry_service import TelemetryService
from backend.simulator.grid_map import build_occupancy_grid
from backend.simulator.world_builder import get_world_layout

DEFAULT_ROBOT_START: Tuple[float, float, float] = (0.0, 0.0, 0.0)


def _rule_based_plan(mission_text: str) -> List[str]:
    """Derive plan steps from mission text. No LLM."""
    text_lower = mission_text.lower().strip()
    steps: List[str] = []
    if "red" in text_lower or "target" in text_lower or not text_lower:
        steps.append("Select target: target")
    else:
        steps.append("Select target: target")
    if "avoid" in text_lower:
        steps.append("Navigate with obstacle avoidance")
    else:
        steps.append("Navigate to target")
    return steps


class OrchestratorService:
    """Runs the autonomy pipeline for a mission: load, plan, perceive, navigate, emit telemetry."""

    def __init__(
        self,
        mission_service: MissionService,
        telemetry_service: TelemetryService,
        world_layout_provider: Optional[
            Callable[[], Tuple[Tuple[float, float, float, float], List[WorldObject], WorldObject]]
        ] = None,
        robot_start_provider: Optional[Callable[[], Tuple[float, float, float]]] = None,
    ) -> None:
        self._mission_service = mission_service
        self._telemetry_service = telemetry_service
        self._get_layout = world_layout_provider or get_world_layout
        self._get_robot_start = robot_start_provider

    def execute(self, mission_id: str) -> Optional[MissionExecutionSummary]:
        """Run pipeline for the mission. Returns None if mission not found."""
        mission = self._mission_service.get(mission_id)
        if mission is None:
            return None

        plan_steps = _rule_based_plan(mission.mission_text)
        self._telemetry_service.record(
            mission_id,
            TelemetryEventType.PLAN_GENERATED,
            TELEMETRY_SOURCE_PLANNER,
            {"plan_steps": plan_steps},
        )

        world_bounds, obstacle_objects, target_object = self._get_layout()
        perception_result = perceive_from_objects(obstacle_objects, target_object)

        if not perception_result.detected_targets:
            self._telemetry_service.record(
                mission_id,
                TelemetryEventType.MISSION_FAILED,
                TELEMETRY_SOURCE_ORCHESTRATOR_SERVICE,
                {"reason": "no_target_found"},
            )
            return self._summary(
                mission_id=mission_id,
                status="failed",
                plan_steps=plan_steps,
                path_found=False,
                message="No target found",
            )

        target = perception_result.detected_targets[0]
        self._telemetry_service.record(
            mission_id,
            TelemetryEventType.PERCEPTION_COMPLETED,
            TELEMETRY_SOURCE_PERCEPTION_AGENT,
            {"target_id": target.object_id, "target_x": target.x, "target_y": target.y},
        )

        robot_start = (
            self._get_robot_start() if self._get_robot_start else DEFAULT_ROBOT_START
        )
        start_x, start_y, _ = robot_start
        obstacle_positions = [(o.x, o.y) for o in obstacle_objects]
        grid = build_occupancy_grid(world_bounds, obstacle_positions)
        nav_result = plan_path(
            grid,
            start_x,
            start_y,
            target.x,
            target.y,
        )

        if not nav_result.path_found:
            self._telemetry_service.record(
                mission_id,
                TelemetryEventType.MISSION_FAILED,
                TELEMETRY_SOURCE_ORCHESTRATOR_SERVICE,
                {"reason": "no_path_found", "message": nav_result.message},
            )
            return self._summary(
                mission_id=mission_id,
                status="failed",
                plan_steps=plan_steps,
                detected_target={"x": target.x, "y": target.y, "object_type": target.object_type},
                path_found=False,
                message=nav_result.message or "No path found",
            )

        self._telemetry_service.record(
            mission_id,
            TelemetryEventType.PATH_COMPUTED,
            TELEMETRY_SOURCE_NAVIGATION_AGENT,
            {"waypoint_count": nav_result.path_length},
        )

        execution_result = None
        try:
            execution_result = run_sim_execution(
                mission_id,
                nav_result.waypoints,
                self._telemetry_service,
                robot_start=robot_start,
            )
        except (RuntimeError, ImportError) as e:
            self._telemetry_service.record(
                mission_id,
                TelemetryEventType.MISSION_FAILED,
                TELEMETRY_SOURCE_ORCHESTRATOR_SERVICE,
                {"reason": "execution_error", "message": str(e)},
            )
            events = self._telemetry_service.get_events_for_mission(mission_id)
            return self._summary(
                mission_id=mission_id,
                status="failed",
                plan_steps=plan_steps,
                detected_target={"x": target.x, "y": target.y, "object_type": target.object_type},
                path_found=True,
                waypoint_count=nav_result.path_length,
                telemetry_count=len(events),
                message=f"Execution failed: {e}",
            )

        if execution_result.execution_status == "failed":
            self._telemetry_service.record(
                mission_id,
                TelemetryEventType.MISSION_FAILED,
                TELEMETRY_SOURCE_ORCHESTRATOR_SERVICE,
                {"reason": "execution_failed", "message": execution_result.message},
            )
            events = self._telemetry_service.get_events_for_mission(mission_id)
            return self._summary(
                mission_id=mission_id,
                status="failed",
                plan_steps=plan_steps,
                detected_target={"x": target.x, "y": target.y, "object_type": target.object_type},
                path_found=True,
                waypoint_count=nav_result.path_length,
                telemetry_count=len(events),
                message=execution_result.message,
                execution_steps=execution_result.execution_steps,
                final_robot_position=execution_result.final_robot_position,
                execution_status=execution_result.execution_status,
            )

        self._telemetry_service.record(
            mission_id,
            TelemetryEventType.MISSION_COMPLETED,
            TELEMETRY_SOURCE_ORCHESTRATOR_SERVICE,
            {"waypoint_count": nav_result.path_length},
        )

        events = self._telemetry_service.get_events_for_mission(mission_id)
        return self._summary(
            mission_id=mission_id,
            status="completed",
            plan_steps=plan_steps,
            detected_target={"x": target.x, "y": target.y, "object_type": target.object_type},
            path_found=True,
            waypoint_count=nav_result.path_length,
            telemetry_count=len(events),
            execution_steps=execution_result.execution_steps,
            final_robot_position=execution_result.final_robot_position,
            execution_status=execution_result.execution_status,
        )

    def _summary(
        self,
        mission_id: str,
        status: str,
        plan_steps: List[str],
        path_found: bool,
        detected_target: Optional[dict] = None,
        waypoint_count: int = 0,
        telemetry_count: Optional[int] = None,
        message: Optional[str] = None,
        execution_steps: Optional[list] = None,
        final_robot_position: Optional[dict] = None,
        execution_status: Optional[str] = None,
    ) -> MissionExecutionSummary:
        if telemetry_count is None:
            telemetry_count = len(self._telemetry_service.get_events_for_mission(mission_id))
        return MissionExecutionSummary(
            mission_id=mission_id,
            status=status,
            plan_steps=plan_steps,
            detected_target=detected_target,
            path_found=path_found,
            waypoint_count=waypoint_count,
            telemetry_count=telemetry_count,
            message=message,
            execution_steps=execution_steps or [],
            final_robot_position=final_robot_position,
            execution_status=execution_status,
        )
