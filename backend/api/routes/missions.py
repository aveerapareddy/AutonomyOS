"""Mission HTTP endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from backend.api.dependencies import (
    get_mission_orchestrator,
    get_mission_service,
    get_orchestrator_service,
)
from backend.schemas.execution import MissionExecutionSummary
from backend.schemas.mission import MissionRecord, MissionRequest, MissionResponse
from backend.services.mission_service import MissionService
from backend.services.mission_orchestrator import MissionOrchestrator
from backend.services.orchestrator_service import OrchestratorService

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


@router.post("/{mission_id}/execute", response_model=MissionExecutionSummary)
def execute_mission(
    mission_id: str,
    orchestrator: OrchestratorService = Depends(get_orchestrator_service),
) -> MissionExecutionSummary:
    """Run plan-perceive-navigate pipeline for the mission."""
    summary = orchestrator.execute(mission_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    return summary
