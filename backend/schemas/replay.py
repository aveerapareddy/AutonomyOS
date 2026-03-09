"""Replay view over telemetry: event-driven decision trace.

Frame order: sequence primary, timestamp secondary (from telemetry). event_type
is the sole classifier for now; no frame_type. For future UI categorization
(planning/perception/navigation/execution), a derived field could be added separately.

target_position on frames comes from payload target_x/target_y. For richer replay,
emitters should include target in execution events (execution_started, waypoint_reached,
mission_completed) when known. Replay response may later add mission_status, started_at,
completed_at for mission-summary linkage; keep current response simple for now.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ReplayFrame(BaseModel):
    """Single replay frame derived from one telemetry event. event_type only; no frame_type."""

    index: int
    event_type: str
    source_component: str
    timestamp: datetime
    robot_position: Optional[dict[str, float]] = None
    target_position: Optional[dict[str, float]] = None
    payload: dict[str, Any] = Field(default_factory=dict)


class MissionReplay(BaseModel):
    """Replay of a mission. Frames ordered by event sequence (primary), then timestamp (secondary).
    Later: optional mission_status, started_at, completed_at for summary linkage."""

    mission_id: str
    frame_count: int
    frames: list[ReplayFrame] = Field(default_factory=list)
