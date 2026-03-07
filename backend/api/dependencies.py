"""Shared FastAPI dependencies for services."""

from typing import Optional

from backend.services.mission_service import MissionService
from backend.services.mission_orchestrator import MissionOrchestrator
from backend.services.telemetry_service import TelemetryService
from backend.storage.repositories.mission_repository import InMemoryMissionRepository

_mission_repository: Optional[InMemoryMissionRepository] = None
_telemetry_service: Optional[TelemetryService] = None


def get_mission_orchestrator() -> MissionOrchestrator:
    """Provide mission orchestrator (create + telemetry)."""
    return MissionOrchestrator(
        mission_service=get_mission_service(),
        telemetry_service=get_telemetry_service(),
    )


def get_mission_service() -> MissionService:
    """Provide mission service. Swap repository for SQLite later."""
    global _mission_repository
    if _mission_repository is None:
        _mission_repository = InMemoryMissionRepository()
    return MissionService(repository=_mission_repository)


def get_telemetry_service() -> TelemetryService:
    """Provide telemetry service. Replace backing store later for SQLite."""
    global _telemetry_service
    if _telemetry_service is None:
        _telemetry_service = TelemetryService()
    return _telemetry_service
