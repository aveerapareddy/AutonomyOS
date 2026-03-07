"""Application-level coordinator for mission creation and related side effects."""

from backend.core.constants import TELEMETRY_SOURCE_API
from backend.schemas.mission import MissionRequest, MissionResponse
from backend.schemas.telemetry import TelemetryEventType
from backend.services.mission_service import MissionService
from backend.services.telemetry_service import TelemetryService


class MissionOrchestrator:
    """Creates missions and emits telemetry. Keeps orchestration out of the API layer."""

    def __init__(
        self,
        mission_service: MissionService,
        telemetry_service: TelemetryService,
    ) -> None:
        self._mission_service = mission_service
        self._telemetry_service = telemetry_service

    def create(self, request: MissionRequest) -> MissionResponse:
        """Create mission and emit mission_received."""
        response = self._mission_service.create(request)
        self._telemetry_service.record(
            response.mission_id,
            TelemetryEventType.MISSION_RECEIVED,
            TELEMETRY_SOURCE_API,
            {"mission_text": request.mission_text},
        )
        return response
