"""Build mission replay from telemetry events. No FastAPI or PyBullet dependency.

Frame order: sequence primary, timestamp secondary. Replay correctness must not
depend on timestamp resolution; sequence gives deterministic reconstruction.
"""

from typing import List, Optional

from backend.schemas.replay import MissionReplay, ReplayFrame
from backend.schemas.telemetry import TelemetryEvent
from backend.services.telemetry_service import TelemetryService


def _extract_robot_position(payload: dict) -> Optional[dict[str, float]]:
    if not payload:
        return None
    x = payload.get("robot_x")
    y = payload.get("robot_y")
    if x is not None and y is not None:
        out: dict[str, float] = {"x": float(x), "y": float(y)}
        theta = payload.get("robot_theta")
        if theta is not None:
            out["theta"] = float(theta)
        return out
    return None


def _extract_target_position(payload: dict) -> Optional[dict[str, float]]:
    if not payload:
        return None
    x = payload.get("target_x")
    y = payload.get("target_y")
    if x is not None and y is not None:
        return {"x": float(x), "y": float(y)}
    return None


def event_to_frame(event: TelemetryEvent, index: int) -> ReplayFrame:
    """Map one telemetry event to a replay frame. Payload is passed through; robot/target normalized."""
    robot_position = _extract_robot_position(event.payload)
    target_position = _extract_target_position(event.payload)
    return ReplayFrame(
        index=index,
        event_type=event.event_type,
        source_component=event.source_component,
        timestamp=event.timestamp,
        robot_position=robot_position,
        target_position=target_position,
        payload=dict(event.payload),
    )


class ReplayService:
    """Builds mission replay from telemetry. Telemetry is source of truth."""

    def __init__(self, telemetry_service: TelemetryService) -> None:
        self._telemetry = telemetry_service

    def build_replay(self, mission_id: str) -> MissionReplay:
        """Return replay for the mission. Frames follow telemetry order: sequence (primary), then timestamp (secondary). Empty if no telemetry."""
        events = self._telemetry.get_events_for_mission(mission_id)
        frames: List[ReplayFrame] = []
        for i, event in enumerate(events):
            frames.append(event_to_frame(event, i))
        return MissionReplay(
            mission_id=mission_id,
            frame_count=len(frames),
            frames=frames,
        )
