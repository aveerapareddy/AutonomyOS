"""SQLite queue with atomic claims, idempotency, bounded subprocesses and cancellation.

Workers share a local filesystem. This is not a multi-host broker.
"""
import json
import os
from pathlib import Path
import re
import signal
import sqlite3
import subprocess
import sys
import time
import uuid
from contextlib import contextmanager
from pydantic import BaseModel,ConfigDict,Field,model_validator
from typing import Literal
from backend.experiments.models import ExperimentRequest
from backend.experiments.runner import digest
from backend.operations.site import SiteSpec

class JobRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    kind:Literal['experiment','site']='experiment'
    experiment:ExperimentRequest|None=None
    site:SiteSpec|None=None
    @model_validator(mode='after')
    def check(self):
        if self.kind=='experiment' and (not self.experiment or self.site):raise ValueError('Experiment job needs only experiment arguments')
        if self.kind=='site' and (not self.site or self.experiment):raise ValueError('Site job needs only site arguments')
        if self.experiment and self.experiment.scenario_count>20:raise ValueError('Queued experiments are limited to 20 scenarios')
        return self

class JobStore:
    def __init__(self,root:Path):
        self.root=root.resolve();self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/'jobs.sqlite3'
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.executescript('''CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, key TEXT UNIQUE NOT NULL, input_hash TEXT NOT NULL,
                request TEXT NOT NULL,status TEXT NOT NULL,created REAL NOT NULL,updated REAL NOT NULL,
                owner TEXT,cancel INTEGER NOT NULL DEFAULT 0,result TEXT,error TEXT);
                CREATE TABLE IF NOT EXISTS events (job TEXT,sequence INTEGER,event TEXT,time REAL,payload TEXT,
                PRIMARY KEY(job,sequence));''')
    @contextmanager
    def connect(self):
        with sqlite3.connect(self.path,timeout=30) as db:
            db.row_factory=sqlite3.Row
            yield db
    def event(self,db,ident,event,payload=None):
        seq=db.execute('SELECT COALESCE(MAX(sequence),0)+1 FROM events WHERE job=?',(ident,)).fetchone()[0]
        db.execute('INSERT INTO events VALUES(?,?,?,?,?)',(ident,seq,event,time.time(),json.dumps(payload or {})))
    def submit(self,request:JobRequest,key:str):
        if not re.fullmatch(r'[A-Za-z0-9_-]{8,80}',key):raise ValueError('Idempotency key must be 8..80 safe characters')
        payload=request.model_dump(mode='json');hashed=digest(payload)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT id,input_hash FROM jobs WHERE key=?',(key,)).fetchone()
            if row:
                if row['input_hash']!=hashed:raise ValueError('Idempotency key already identifies different input')
                ident=row['id']
            else:
                if db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]>=100:raise ValueError('Local queue retention limit reached (100 jobs)')
                ident=uuid.uuid4().hex;now=time.time()
                db.execute('INSERT INTO jobs(id,key,input_hash,request,status,created,updated) VALUES(?,?,?,?,?,?,?)',
                           (ident,key,hashed,json.dumps(payload),'queued',now,now))
                self.event(db,ident,'submitted',{'input_hash':hashed})
        return self.get(ident)
    def get(self,ident):
        if not re.fullmatch(r'[0-9a-f]{32}',ident):raise ValueError('Invalid job identifier')
        with self.connect() as db:
            row=db.execute('SELECT * FROM jobs WHERE id=?',(ident,)).fetchone()
            if not row:raise ValueError('Job not found')
            result=dict(row)
            result['events']=[{**dict(r),'payload':json.loads(r['payload'])} for r in db.execute('SELECT * FROM events WHERE job=? ORDER BY sequence',(ident,))]
        for key in ('request','result'):result[key]=json.loads(result[key]) if result[key] else None
        return result
    def list(self):
        with self.connect() as db:
            return [dict(r) for r in db.execute('SELECT id,status,created,updated,input_hash FROM jobs ORDER BY created DESC LIMIT 100')]
    def cancel(self,ident):
        self.get(ident)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT status FROM jobs WHERE id=?',(ident,)).fetchone()
            if row['status'] in {'queued','running'}:
                status='cancelled' if row['status']=='queued' else 'running'
                db.execute('UPDATE jobs SET cancel=1,status=?,updated=? WHERE id=?',(status,time.time(),ident))
                self.event(db,ident,'cancellation_requested')
        return self.get(ident)
    def claim(self):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            # Stale claims are terminal, never automatically duplicated. Child watchdog is 60s.
            for row in db.execute("SELECT id FROM jobs WHERE status='running' AND updated<?",(time.time()-120,)).fetchall():
                db.execute("UPDATE jobs SET status='interrupted',error='Worker heartbeat expired; manual investigation required' WHERE id=?",(row['id'],))
                self.event(db,row['id'],'interrupted',{'automatic_retry':False})
            if db.execute("SELECT COUNT(*) FROM jobs WHERE status='running'").fetchone()[0]>=2:return None
            row=db.execute("SELECT id FROM jobs WHERE status='queued' AND cancel=0 ORDER BY created LIMIT 1").fetchone()
            if not row:return None
            ident=row['id'];owner=uuid.uuid4().hex
            db.execute("UPDATE jobs SET status='running',owner=?,updated=? WHERE id=?",(owner,time.time(),ident))
            self.event(db,ident,'claimed',{'owner':owner})
        return self.get(ident)
    def finish(self,ident,status,result=None,error=None):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT cancel,status FROM jobs WHERE id=?',(ident,)).fetchone()
            if row['status']!='running':return
            # Cancellation racing with completion has terminal priority.
            status='cancelled' if row['cancel'] else status
            db.execute('UPDATE jobs SET status=?,result=?,error=?,updated=? WHERE id=?',
                       (status,json.dumps(result) if result is not None else None,error,time.time(),ident))
            self.event(db,ident,status,{'error':error,'automatic_retry':False})
    def run_one(self):
        item=self.claim()
        if not item:return False
        ident=item['id'];directory=self.root/ident;directory.mkdir(exist_ok=True)
        (directory/'request.json').write_text(json.dumps(item['request'],indent=2)+'\n')
        process=None
        try:
            env={**os.environ,'AUTONOMY_PLANNER_MODE':'rule_based'}
            with (directory/'worker.log').open('wb') as log:
                process=subprocess.Popen([sys.executable,'-m','scripts.execute_job','--directory',str(directory)],
                  cwd=Path(__file__).resolve().parents[2],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                start=time.monotonic();last=0
                while process.poll() is None:
                    now=time.monotonic()
                    cancelled=self.get(ident)['cancel']
                    if cancelled or now-start>65:
                        os.killpg(process.pid,signal.SIGKILL);process.wait()
                        self.finish(ident,'cancelled' if cancelled else 'failed',error='Cancelled' if cancelled else 'Job timeout')
                        return True
                    if now-last>1:
                        with self.connect() as db:db.execute('UPDATE jobs SET updated=? WHERE id=? AND owner=?',(time.time(),ident,item['owner']))
                        last=now
                    time.sleep(.05)
            if process.returncode:raise ValueError(f'Worker exited {process.returncode}; inspect worker.log')
            result=json.loads((directory/'result.json').read_text())
            if result.get('input_hash')!=item['input_hash']:raise ValueError('Worker result input hash mismatch')
            self.finish(ident,'completed',result)
        except Exception as exc:
            if process and process.poll() is None:os.killpg(process.pid,signal.SIGKILL);process.wait()
            self.finish(ident,'failed',error=str(exc))
        return True
