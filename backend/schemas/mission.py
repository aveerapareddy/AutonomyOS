"""Mission request, response, and record schemas."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class MissionStatus(str, Enum):
    """Stable mission lifecycle states."""

    RECEIVED = "received"
    PLANNED = "planned"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


class MissionRequest(BaseModel):
    """Input for creating or submitting a mission."""

    mission_text: str = Field(..., min_length=1)
    world_id: Optional[str] = None

    @field_validator("mission_text", mode="before")
    @classmethod
    def trim_and_reject_blank(cls, v: str) -> str:
        s = (v or "").strip()
        if not s:
            raise ValueError("mission_text cannot be empty or blank")
        return s


class MissionResponse(BaseModel):
    """Mission creation or status response."""

    mission_id: str
    status: MissionStatus
    created_at: datetime


class MissionRecord(BaseModel):
    """Full mission record for retrieval."""

    mission_id: str
    mission_text: str
    world_id: Optional[str] = None
    status: MissionStatus
    created_at: datetime
