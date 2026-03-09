"""WaypointExecutor and execution flow tests."""

import pytest

from backend.schemas.navigation import Waypoint
from backend.services.telemetry_service import TelemetryService
from backend.simulator.execution_engine import (
    ExecutionConfig,
    WaypointExecutor,
)
from backend.simulator.environment import SimulationEnvironment


def test_waypoint_executor_reaches_target() -> None:
    """Executor reaches all waypoints and returns completed."""
    pytest.importorskip("pybullet")
    env = SimulationEnvironment(use_gui=False)
    try:
        telemetry = TelemetryService()
        executor = WaypointExecutor(env, "m1", telemetry)
        waypoints = [
            Waypoint(x=0.5, y=0.0),
            Waypoint(x=1.0, y=0.0),
            Waypoint(x=1.0, y=0.5),
        ]
        result = executor.execute(waypoints)
        assert result.execution_status == "completed"
        assert len(result.execution_steps) == 3
        assert all(s.reached for s in result.execution_steps)
        assert result.final_robot_position is not None
    finally:
        env.shutdown()


def test_waypoint_executor_emits_telemetry() -> None:
    """Execution emits execution_started, waypoint_reached, execution_completed."""
    pytest.importorskip("pybullet")
    env = SimulationEnvironment(use_gui=False)
    try:
        telemetry = TelemetryService()
        executor = WaypointExecutor(env, "m2", telemetry)
        waypoints = [Waypoint(x=0.3, y=0.0)]
        executor.execute(waypoints)
        events = telemetry.get_events_for_mission("m2")
        event_types = [e.event_type for e in events]
        assert "execution_started" in event_types
        assert "waypoint_reached" in event_types
        assert "execution_completed" in event_types
    finally:
        env.shutdown()


def test_waypoint_executor_failure_max_steps() -> None:
    """When max_steps_per_waypoint exceeded, execution fails cleanly."""
    pytest.importorskip("pybullet")
    env = SimulationEnvironment(use_gui=False)
    try:
        telemetry = TelemetryService()
        config = ExecutionConfig(max_steps_per_waypoint=2, waypoint_tolerance=0.01)
        executor = WaypointExecutor(env, "m3", telemetry, config=config)
        waypoints = [Waypoint(x=10.0, y=10.0)]
        result = executor.execute(waypoints)
        assert result.execution_status == "failed"
        assert result.message is not None
        assert "max steps" in result.message.lower() or "exceeded" in result.message.lower()
        assert result.final_robot_position is not None
        events = telemetry.get_events_for_mission("m3")
        event_types = [e.event_type for e in events]
        assert "execution_failed" in event_types
    finally:
        env.shutdown()
