"""Telemetry event schema."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TelemetryEvent(BaseModel):
    """Single telemetry event for a mission."""

    event_id: str
    mission_id: str
    timestamp: datetime
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
