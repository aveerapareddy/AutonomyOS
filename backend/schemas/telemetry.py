"""Telemetry event schemas and event types."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TelemetryEventType(str, Enum):
    """Stable event types for replay and benchmarking."""

    MISSION_RECEIVED = "mission_received"
    PLAN_GENERATED = "plan_generated"
    PERCEPTION_COMPLETED = "perception_completed"
    PATH_COMPUTED = "path_computed"
    OBSTACLE_DETECTED = "obstacle_detected"
    REPLANNING_STARTED = "replanning_started"
    MISSION_COMPLETED = "mission_completed"
    MISSION_FAILED = "mission_failed"
    EXECUTION_STARTED = "execution_started"
    WAYPOINT_REACHED = "waypoint_reached"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"


class TelemetryEvent(BaseModel):
    """Single telemetry event for a mission."""

    event_id: str
    mission_id: str
    sequence: int
    timestamp: datetime
    event_type: str
    source_component: str
    payload: dict[str, Any] = Field(default_factory=dict)


class TelemetryTimeline(BaseModel):
    """Ordered list of events for a mission."""

    mission_id: str
    events: list[TelemetryEvent] = Field(default_factory=list)


class TelemetryQueryResponse(BaseModel):
    """API response for telemetry retrieval."""

    mission_id: str
    events: list[TelemetryEvent] = Field(default_factory=list)
    count: int = 0
