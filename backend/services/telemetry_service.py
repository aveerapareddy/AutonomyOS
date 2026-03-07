"""Event recording and retrieval for mission replay and benchmarking."""

import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import List

from backend.schemas.telemetry import TelemetryEvent, TelemetryEventType


class TelemetryService:
    """Records and retrieves telemetry events. In-memory store; replaceable with SQLite later."""

    def __init__(self) -> None:
        self._store: dict[str, List[TelemetryEvent]] = defaultdict(list)
        self._sequence: dict[str, int] = defaultdict(int)

    def record(
        self,
        mission_id: str,
        event_type: str | TelemetryEventType,
        source_component: str,
        payload: dict | None = None,
    ) -> TelemetryEvent:
        """Append one event. Returns the recorded event."""
        event_type_str = event_type.value if isinstance(event_type, TelemetryEventType) else event_type
        now = datetime.now(timezone.utc)
        self._sequence[mission_id] += 1
        seq = self._sequence[mission_id]
        event = TelemetryEvent(
            event_id=uuid.uuid4().hex,
            mission_id=mission_id,
            sequence=seq,
            timestamp=now,
            event_type=event_type_str,
            source_component=source_component,
            payload=payload or {},
        )
        self._store[mission_id].append(event)
        return event

    def get_events_for_mission(self, mission_id: str) -> List[TelemetryEvent]:
        """Return events for the mission in chronological order (by sequence, then timestamp)."""
        events = self._store.get(mission_id, [])
        return sorted(events, key=lambda e: (e.sequence, e.timestamp))
