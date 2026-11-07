"""Transactional local mission/event journal; each operation owns its connection."""

import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from backend.schemas.mission import MissionRecord
from backend.schemas.telemetry import TelemetryEvent


class SQLiteJournal:
    def __init__(self, path: str) -> None:
        if path == ':memory:':
            raise ValueError('Use a file path for a durable journal')
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.executescript('''
                CREATE TABLE IF NOT EXISTS missions (
                    mission_id TEXT PRIMARY KEY, record TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    mission_id TEXT NOT NULL, sequence INTEGER NOT NULL,
                    record TEXT NOT NULL, PRIMARY KEY(mission_id, sequence)
                );
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def add(self, record: MissionRecord) -> None:
        with self.connect() as db:
            db.execute('INSERT INTO missions VALUES (?, ?)', (record.mission_id, record.model_dump_json()))

    def get(self, mission_id: str) -> MissionRecord | None:
        with self.connect() as db:
            row = db.execute('SELECT record FROM missions WHERE mission_id=?', (mission_id,)).fetchone()
        return MissionRecord.model_validate_json(row[0]) if row else None

    def append(self, mission_id: str, event_type: str, source: str, payload: dict) -> TelemetryEvent:
        with self.connect() as db:
            # Serializes sequence allocation across threads AND independent processes.
            db.execute('BEGIN IMMEDIATE')
            sequence = db.execute('SELECT COALESCE(MAX(sequence), 0) + 1 FROM events WHERE mission_id=?', (mission_id,)).fetchone()[0]
            event = TelemetryEvent(event_id=uuid.uuid4().hex, mission_id=mission_id,
                                   sequence=sequence, timestamp=datetime.now(timezone.utc),
                                   event_type=event_type, source_component=source, payload=payload)
            db.execute('INSERT INTO events VALUES (?, ?, ?)', (mission_id, sequence, event.model_dump_json()))
        return event

    def events(self, mission_id: str, after_sequence: int = 0) -> list[TelemetryEvent]:
        with self.connect() as db:
            rows = db.execute('SELECT record FROM events WHERE mission_id=? AND sequence>? ORDER BY sequence', (mission_id, after_sequence)).fetchall()
        return [TelemetryEvent.model_validate_json(row[0]) for row in rows]
