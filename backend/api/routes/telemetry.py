"""Telemetry endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from backend.api.dependencies import get_mission_service, get_telemetry_service
from backend.schemas.telemetry import TelemetryQueryResponse
from backend.services.mission_service import MissionService
from backend.services.telemetry_service import TelemetryService

router = APIRouter(prefix="/missions", tags=["telemetry"])


@router.get("/{mission_id}/telemetry", response_model=TelemetryQueryResponse)
def get_mission_telemetry(
    mission_id: str,
    mission_service: MissionService = Depends(get_mission_service),
    telemetry_service: TelemetryService = Depends(get_telemetry_service),
) -> TelemetryQueryResponse:
    """Return ordered event timeline for a mission. 404 if mission does not exist."""
    if mission_service.get(mission_id) is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    events = telemetry_service.get_events_for_mission(mission_id)
    return TelemetryQueryResponse(mission_id=mission_id, events=events, count=len(events))
