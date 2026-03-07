"""Mission lifecycle: create and retrieve."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from backend.schemas.mission import MissionRecord, MissionRequest, MissionResponse, MissionStatus
from backend.storage.repositories.mission_repository import InMemoryMissionRepository, MissionRepository


class MissionService:
    """Creates and retrieves missions. Storage is injectable for testing and future SQLite."""

    def __init__(self, repository: Optional[MissionRepository] = None) -> None:
        self._repo = repository or InMemoryMissionRepository()

    def create(self, request: MissionRequest) -> MissionResponse:
        """Create a mission and return the creation response."""
        now = datetime.now(timezone.utc)
        mission_id = uuid.uuid4().hex
        record = MissionRecord(
            mission_id=mission_id,
            mission_text=request.mission_text,
            world_id=request.world_id,
            status=MissionStatus.RECEIVED,
            created_at=now,
        )
        self._repo.add(record)
        return MissionResponse(
            mission_id=record.mission_id,
            status=record.status,
            created_at=record.created_at,
        )

    def get(self, mission_id: str) -> Optional[MissionRecord]:
        """Return full mission record or None."""
        return self._repo.get(mission_id)
