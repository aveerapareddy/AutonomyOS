"""Mission HTTP endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from backend.api.dependencies import get_mission_orchestrator, get_mission_service
from backend.schemas.mission import MissionRecord, MissionRequest, MissionResponse
from backend.services.mission_service import MissionService
from backend.services.mission_orchestrator import MissionOrchestrator

router = APIRouter(prefix="/missions", tags=["missions"])


@router.post("", response_model=MissionResponse, status_code=201)
def create_mission(
    body: MissionRequest,
    orchestrator: MissionOrchestrator = Depends(get_mission_orchestrator),
) -> MissionResponse:
    """Create a mission from natural language input."""
    return orchestrator.create(body)


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
