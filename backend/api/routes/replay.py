"""Replay endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from backend.api.dependencies import get_mission_service, get_replay_service
from backend.schemas.replay import MissionReplay
from backend.services.mission_service import MissionService
from backend.services.replay_service import ReplayService

router = APIRouter(prefix="/missions", tags=["replay"])


@router.get("/{mission_id}/replay", response_model=MissionReplay)
def get_mission_replay(
    mission_id: str,
    mission_service: MissionService = Depends(get_mission_service),
    replay_service: ReplayService = Depends(get_replay_service),
) -> MissionReplay:
    """Return event-driven replay for the mission. 404 if mission does not exist."""
    if mission_service.get(mission_id) is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    return replay_service.build_replay(mission_id)
