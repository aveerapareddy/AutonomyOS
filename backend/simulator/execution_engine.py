"""Waypoint execution: drive robot through navigation path in the simulator."""

import math
from dataclasses import dataclass
from typing import List, Optional

from backend.core.constants import TELEMETRY_SOURCE_EXECUTION_AGENT
from backend.schemas.execution import ExecutionResult, ExecutionStep
from backend.schemas.navigation import Waypoint
from backend.schemas.telemetry import TelemetryEventType
from backend.services.telemetry_service import TelemetryService
from backend.simulator.actions import RobotAction
from backend.simulator.environment import SimulationEnvironment
from backend.simulator.robot import RobotPose

WAYPOINT_TOLERANCE = 0.15
TURN_THRESHOLD_RAD = 0.08
MAX_STEPS_PER_WAYPOINT = 8000


def _normalize_angle(angle: float) -> float:
    return math.atan2(math.sin(angle), math.cos(angle))


def _distance(ax: float, ay: float, bx: float, by: float) -> float:
    return math.hypot(bx - ax, by - ay)


def _heading_to(rx: float, ry: float, tx: float, ty: float) -> float:
    return math.atan2(ty - ry, tx - rx)


@dataclass
class ExecutionConfig:
    waypoint_tolerance: float = WAYPOINT_TOLERANCE
    turn_threshold_rad: float = TURN_THRESHOLD_RAD
    max_steps_per_waypoint: int = MAX_STEPS_PER_WAYPOINT


class WaypointExecutor:
    """Drives the robot through a list of waypoints; emits telemetry."""

    def __init__(
        self,
        env: SimulationEnvironment,
        mission_id: str,
        telemetry_service: TelemetryService,
        config: Optional[ExecutionConfig] = None,
    ) -> None:
        self._env = env
        self._mission_id = mission_id
        self._telemetry = telemetry_service
        self._config = config or ExecutionConfig()

    def execute(self, waypoints: List[Waypoint]) -> ExecutionResult:
        if not waypoints:
            return ExecutionResult(
                execution_status="completed",
                execution_steps=[],
                final_robot_position=_pose_to_dict(self._env.get_robot_pose()),
                message="No waypoints",
            )

        pose = self._env.get_robot_pose()
        self._telemetry.record(
            self._mission_id,
            TelemetryEventType.EXECUTION_STARTED,
            TELEMETRY_SOURCE_EXECUTION_AGENT,
            {
                "waypoint_count": len(waypoints),
                "robot_x": pose.x,
                "robot_y": pose.y,
                "robot_theta": pose.theta,
            },
        )

        steps: List[ExecutionStep] = []
        tol = self._config.waypoint_tolerance
        turn_thresh = self._config.turn_threshold_rad
        max_steps = self._config.max_steps_per_waypoint

        for idx, wp in enumerate(waypoints):
            step_count = 0
            while step_count < max_steps:
                pose = self._env.get_robot_pose()
                dist = _distance(pose.x, pose.y, wp.x, wp.y)
                if dist < tol:
                    steps.append(
                        ExecutionStep(waypoint_index=idx, target_x=wp.x, target_y=wp.y, reached=True)
                    )
                    self._telemetry.record(
                        self._mission_id,
                        TelemetryEventType.WAYPOINT_REACHED,
                        TELEMETRY_SOURCE_EXECUTION_AGENT,
                        {
                            "waypoint_index": idx,
                            "target_x": wp.x,
                            "target_y": wp.y,
                            "robot_x": pose.x,
                            "robot_y": pose.y,
                        },
                    )
                    break

                goal_heading = _heading_to(pose.x, pose.y, wp.x, wp.y)
                diff = _normalize_angle(goal_heading - pose.theta)
                if abs(diff) < turn_thresh:
                    self._env.step(RobotAction.FORWARD)
                elif diff > 0:
                    self._env.step(RobotAction.TURN_LEFT)
                else:
                    self._env.step(RobotAction.TURN_RIGHT)
                step_count += 1
            else:
                pose = self._env.get_robot_pose()
                steps.append(
                    ExecutionStep(waypoint_index=idx, target_x=wp.x, target_y=wp.y, reached=False)
                )
                self._telemetry.record(
                    self._mission_id,
                    TelemetryEventType.EXECUTION_FAILED,
                    TELEMETRY_SOURCE_EXECUTION_AGENT,
                    {
                        "reason": "max_steps_per_waypoint",
                        "waypoint_index": idx,
                        "robot_x": pose.x,
                        "robot_y": pose.y,
                        "target_x": wp.x,
                        "target_y": wp.y,
                    },
                )
                return ExecutionResult(
                    execution_status="failed",
                    execution_steps=steps,
                    final_robot_position=_pose_to_dict(pose),
                    message=f"Max steps exceeded at waypoint {idx}",
                )

        pose = self._env.get_robot_pose()
        self._telemetry.record(
            self._mission_id,
            TelemetryEventType.EXECUTION_COMPLETED,
            TELEMETRY_SOURCE_EXECUTION_AGENT,
            {
                "waypoints_reached": len(waypoints),
                "robot_x": pose.x,
                "robot_y": pose.y,
                "robot_theta": pose.theta,
            },
        )
        return ExecutionResult(
            execution_status="completed",
            execution_steps=steps,
            final_robot_position=_pose_to_dict(pose),
        )


def _pose_to_dict(pose: RobotPose) -> dict:
    return {"x": pose.x, "y": pose.y, "theta": pose.theta}
