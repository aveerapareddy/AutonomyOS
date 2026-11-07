"""Local durable experiment state, append-only event sequence and report storage."""
import json
from contextlib import contextmanager
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat()


class Ledger:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY, status TEXT NOT NULL,
                    request TEXT NOT NULL, report TEXT);
                CREATE TABLE IF NOT EXISTS events (
                    run_id TEXT NOT NULL REFERENCES runs(id), sequence INTEGER NOT NULL,
                    time TEXT NOT NULL, stage TEXT NOT NULL, payload TEXT NOT NULL,
                    PRIMARY KEY(run_id, sequence));
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        try:
            db.execute("PRAGMA foreign_keys=ON")
            with db:
                yield db
        finally:
            db.close()

    def create(self, run_id, request):
        with self.connect() as db:
            db.execute("INSERT INTO runs VALUES (?, 'created', ?, NULL)",
                       (run_id, json.dumps(request)))

    def event(self, run_id, stage, payload):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            seq = db.execute("SELECT COALESCE(MAX(sequence),0)+1 FROM events WHERE run_id=?",
                             (run_id,)).fetchone()[0]
            db.execute("INSERT INTO events VALUES (?,?,?,?,?)",
                       (run_id, seq, now(), stage, json.dumps(payload)))
            db.execute("UPDATE runs SET status=? WHERE id=?", (stage, run_id))

    def finish(self, report):
        with self.connect() as db:
            db.execute("UPDATE runs SET status=?, report=? WHERE id=?",
                       (report.status, report.model_dump_json(), report.run_id))

    def read(self, run_id):
        with self.connect() as db:
            row = db.execute("SELECT status,request,report FROM runs WHERE id=?", (run_id,)).fetchone()
            if row is None:
                raise KeyError(run_id)
            events = db.execute("SELECT sequence,time,stage,payload FROM events WHERE run_id=? ORDER BY sequence",
                                (run_id,)).fetchall()
        return {"run_id": run_id, "status": row[0], "request": json.loads(row[1]),
                "report": json.loads(row[2]) if row[2] else None,
                "events": [{"sequence": s, "time": t, "stage": st, "payload": json.loads(p)}
                           for s, t, st, p in events]}
