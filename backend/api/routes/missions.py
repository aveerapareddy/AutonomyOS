"""Mission HTTP endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from backend.schemas.mission import MissionRecord, MissionRequest, MissionResponse
from backend.services.mission_service import MissionService
from backend.storage.repositories.mission_repository import InMemoryMissionRepository

router = APIRouter(prefix="/missions", tags=["missions"])

_mission_repository: Optional[InMemoryMissionRepository] = None


def get_mission_service() -> MissionService:
    """Provide mission service. Swap repository for SQLite later."""
    global _mission_repository
    if _mission_repository is None:
        _mission_repository = InMemoryMissionRepository()
    return MissionService(repository=_mission_repository)


@router.post("", response_model=MissionResponse, status_code=201)
def create_mission(
    body: MissionRequest,
    service: MissionService = Depends(get_mission_service),
) -> MissionResponse:
    """Create a mission from natural language input."""
    return service.create(body)


@router.get("/{mission_id}", response_model=MissionRecord)
def get_mission(
    mission_id: str,
    service: MissionService = Depends(get_mission_service),
) -> MissionRecord:
    """Return full mission record by id."""
    record = service.get(mission_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    return record
