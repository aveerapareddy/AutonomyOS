"""Mission storage abstraction."""

from typing import Optional, Protocol

from backend.schemas.mission import MissionRecord


class MissionRepository(Protocol):
    """Storage contract for missions. Swap implementation for SQLite later."""

    def add(self, record: MissionRecord) -> None:
        """Persist a mission record."""
        ...

    def get(self, mission_id: str) -> Optional[MissionRecord]:
        """Return mission by id or None if not found."""
        ...


class InMemoryMissionRepository:
    """In-memory mission store. Suitable for single-process and tests."""

    def __init__(self) -> None:
        self._store: dict[str, MissionRecord] = {}

    def add(self, record: MissionRecord) -> None:
        self._store[record.mission_id] = record

    def get(self, mission_id: str) -> Optional[MissionRecord]:
        return self._store.get(mission_id)
