"""Governed model-to-experiment workflow, isolated from mission/UI persistence.

The local operator CLI is trusted. This is not a multi-user authentication service.
Model outputs cannot approve proposals, select shell commands or choose output paths.
"""
from contextlib import contextmanager
import hashlib
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
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from backend.experiments.models import ExperimentRequest, ExperimentReport
from backend.experiments.runner import digest
from backend.integrations.huggingface import validate_proposal


class WorkflowPolicy(BaseModel):
    model_config = ConfigDict(extra='forbid')
    max_scenarios: int = Field(default=100, ge=1, le=100)
    max_model_tokens: int = Field(default=4096, ge=1, le=32768)
    max_tool_calls: int = Field(default=1, ge=0, le=1)
    approval_ttl_seconds: int = Field(default=3600, ge=1, le=86400)
    tool_timeout_seconds: float = Field(default=60.0, gt=0, le=1200, allow_inf_nan=False)
    require_human_review: bool = True


class ModelSource(BaseModel):
    model_config = ConfigDict(extra='forbid')
    model_id: str = Field(min_length=1, max_length=200)
    revision: str = Field(pattern=r'^[0-9a-f]{40}$')
    artifact_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    accounting_trust: Literal['imported_local_report'] = 'imported_local_report'


class ToolProposal(BaseModel):
    model_config = ConfigDict(extra='forbid')
    tool: Literal['run_experiment'] = 'run_experiment'
    arguments: ExperimentRequest
    source: ModelSource


class WorkflowError(ValueError):
    pass


class AgentWorkflow:
    """Durable review/claim state plus one allowlisted, process-isolated tool call."""
    def __init__(self, root: Path, policy: WorkflowPolicy | None = None):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / 'agent-workflows.sqlite'
        self.policy = policy or WorkflowPolicy()
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS proposals (
                    id TEXT PRIMARY KEY, body TEXT NOT NULL, digest TEXT NOT NULL,
                    policy TEXT NOT NULL, status TEXT NOT NULL, created_at REAL NOT NULL,
                    expires_at REAL NOT NULL, approval TEXT, report TEXT,
                    call_count INTEGER NOT NULL DEFAULT 0, error TEXT);
                CREATE TABLE IF NOT EXISTS workflow_events (
                    workflow_id TEXT NOT NULL REFERENCES proposals(id), sequence INTEGER NOT NULL,
                    time REAL NOT NULL, event TEXT NOT NULL, payload TEXT NOT NULL,
                    PRIMARY KEY(workflow_id, sequence));
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.db_path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    def _event(self, db, workflow_id, event, payload):
        seq = db.execute('SELECT COALESCE(MAX(sequence),0)+1 FROM workflow_events WHERE workflow_id=?',
                         (workflow_id,)).fetchone()[0]
        db.execute('INSERT INTO workflow_events VALUES (?,?,?,?,?)',
                   (workflow_id, seq, time.time(), event, json.dumps(payload, allow_nan=False)))

    def _row(self, db, workflow_id):
        if not re.fullmatch(r'[0-9a-f]{32}', workflow_id):
            raise WorkflowError('Invalid workflow identifier')
        row = db.execute('SELECT * FROM proposals WHERE id=?', (workflow_id,)).fetchone()
        if row is None:
            raise WorkflowError('Workflow not found')
        return row

    def _integrity(self, row):
        try:
            proposal = ToolProposal.model_validate_json(row['body'])
            stored_policy = WorkflowPolicy.model_validate_json(row['policy'])
        except ValueError as exc:
            raise WorkflowError('Stored proposal or policy failed validation') from exc
        expected = digest({'proposal': proposal.model_dump(mode='json'), 'policy': stored_policy.model_dump()})
        if row['digest'] != expected:
            raise WorkflowError('Stored proposal changed after submission')
        if stored_policy != self.policy:
            raise WorkflowError('Policy changed; submit and approve a new proposal')
        self._check_budget(proposal)
        return proposal

    def _check_budget(self, proposal):
        if proposal.arguments.scenario_count > self.policy.max_scenarios:
            raise WorkflowError('Scenario budget exceeded')
        if proposal.source.input_tokens + proposal.source.output_tokens > self.policy.max_model_tokens:
            raise WorkflowError('Recorded model-token budget exceeded')

    def submit(self, proposal: ToolProposal):
        self._check_budget(proposal)
        workflow_id = uuid.uuid4().hex
        body = proposal.model_dump_json()
        approval_digest = digest({'proposal': proposal.model_dump(mode='json'), 'policy': self.policy.model_dump()})
        now = time.time()
        with self.connect() as db:
            db.execute('INSERT INTO proposals(id,body,digest,policy,status,created_at,expires_at) VALUES(?,?,?,?,?,?,?)',
                       (workflow_id, body, approval_digest, self.policy.model_dump_json(), 'awaiting_approval',
                        now, now + self.policy.approval_ttl_seconds))
            self._event(db, workflow_id, 'proposal_submitted', {'role':'model_planner', 'digest':approval_digest,
                         'tool':proposal.tool, 'source':proposal.source.model_dump()})
        return self.get(workflow_id)

    def submit_inference(self, artifact: Path):
        raw = artifact.read_bytes()
        if len(raw) > 256_000:
            raise WorkflowError('Inference artifact exceeds the import size limit')
        data = json.loads(raw)
        # Revalidate raw output; never trust the imported validated/proposal flags alone.
        arguments = validate_proposal(data['raw_output'])
        if data.get('validated') is not True or arguments.model_dump() != data.get('proposal'):
            raise WorkflowError('Raw output and validated proposal disagree')
        source = ModelSource(model_id=data['model_id'], revision=data['revision'],
                             artifact_sha256=hashlib.sha256(raw).hexdigest(),
                             input_tokens=data['input_tokens'], output_tokens=data['output_tokens'])
        result = self.submit(ToolProposal(arguments=arguments, source=source))
        directory = self.root / result['id']
        try:
            directory.mkdir()
            (directory / 'inference.json').write_bytes(raw)
        except OSError as exc:
            with self.connect() as db:
                db.execute("UPDATE proposals SET status='failed',error=? WHERE id=?", (str(exc), result['id']))
                self._event(db, result['id'], 'input_artifact_failed', {'error_type':type(exc).__name__, 'message':str(exc)})
            raise
        return result

    def _audit_denial(self, workflow_id, operation, error):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            try:
                row = self._row(db, workflow_id)
            except WorkflowError:
                return
            if row['status'] in {'failed', 'completed'}:
                return
            if time.time() > row['expires_at'] and row['status'] in {'approved', 'awaiting_approval'}:
                db.execute("UPDATE proposals SET status='expired' WHERE id=?", (workflow_id,))
            self._event(db, workflow_id, operation + '_denied', {'reason':str(error), 'tool_dispatched':False})

    def approve(self, workflow_id, expected_digest, actor, review_kind='human'):
        try:
            return self._approve(workflow_id, expected_digest, actor, review_kind)
        except WorkflowError as exc:
            self._audit_denial(workflow_id, 'approval', exc)
            raise

    def _approve(self, workflow_id, expected_digest, actor, review_kind='human'):
        if not isinstance(actor, str) or not 1 <= len(actor.strip()) <= 100:
            raise WorkflowError('An identified local reviewer is required')
        if review_kind not in {'human', 'automated_validation'}:
            raise WorkflowError('Unknown review kind')
        if self.policy.require_human_review and review_kind != 'human':
            raise WorkflowError('Human review is required by policy')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = self._row(db, workflow_id)
            self._integrity(row)
            if row['status'] != 'awaiting_approval':
                raise WorkflowError('Proposal is not awaiting approval')
            if time.time() > row['expires_at']:
                raise WorkflowError('Proposal approval expired')
            if expected_digest != row['digest']:
                raise WorkflowError('Approval does not match the exact proposal and policy')
            approval = {'actor':actor.strip(), 'kind':review_kind, 'digest':expected_digest, 'time':time.time(),
                        'authentication':'trusted local operator; shared API token or CLI, no individual identity attestation'}
            db.execute("UPDATE proposals SET status='approved',approval=? WHERE id=?",
                       (json.dumps(approval), workflow_id))
            self._event(db, workflow_id, 'proposal_approved', approval)
        return self.get(workflow_id)

    def reject(self, workflow_id, actor, reason):
        if not actor.strip() or not reason.strip():
            raise WorkflowError('Reviewer and rejection reason are required')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = self._row(db, workflow_id)
            if row['status'] not in {'awaiting_approval', 'approved'}:
                raise WorkflowError('Cannot reject a running or terminal workflow')
            db.execute("UPDATE proposals SET status='rejected' WHERE id=?", (workflow_id,))
            self._event(db, workflow_id, 'proposal_rejected', {'actor':actor, 'reason':reason})
        return self.get(workflow_id)

    def execute(self, workflow_id):
        try:
            return self._execute(workflow_id)
        except WorkflowError as exc:
            self._audit_denial(workflow_id, 'execution', exc)
            raise

    def _execute(self, workflow_id):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = self._row(db, workflow_id)
            proposal = self._integrity(row)
            if row['status'] == 'completed':
                return json.loads(row['report'])
            if row['status'] != 'approved':
                raise WorkflowError('Exact proposal approval is required; running/failed work is not automatically retried')
            if time.time() > row['expires_at']:
                raise WorkflowError('Approved proposal expired')
            approval = json.loads(row['approval'])
            if approval['digest'] != row['digest']:
                raise WorkflowError('Approval no longer matches proposal')
            if self.policy.require_human_review and approval['kind'] != 'human':
                raise WorkflowError('Human review is required')
            if row['call_count'] >= self.policy.max_tool_calls:
                raise WorkflowError('Tool-call budget exhausted')
            db.execute("UPDATE proposals SET status='running',call_count=call_count+1 WHERE id=?", (workflow_id,))
            self._event(db, workflow_id, 'tool_started', {'role':'simulation_operator', 'tool':proposal.tool,
                         'timeout_seconds':self.policy.tool_timeout_seconds, 'call_index':row['call_count']+1})
        directory = self.root / workflow_id
        start = time.monotonic()
        try:
            directory.mkdir(exist_ok=True)
            request_path = directory / 'request.json'
            request_path.write_text(proposal.arguments.model_dump_json(indent=2) + '\n')
            command = [sys.executable, '-m', 'scripts.execute_agent_tool', '--request', str(request_path),
                       '--output', str(directory / 'run'), '--ledger', str(directory / 'experiment.sqlite')]
            code = self._invoke(command, directory / 'tool.log', self.policy.tool_timeout_seconds)
            if code != 0:
                raise WorkflowError('Experiment tool failed with exit code ' + str(code))
            report = ExperimentReport.model_validate_json((directory / 'run/report.json').read_text())
            if report.request != proposal.arguments or report.status != 'completed' or not report.evaluation_passed:
                raise WorkflowError('Tool report failed independent request/status/evaluation validation')
            result = {'workflow_id':workflow_id, 'experiment':report.model_dump(mode='json'),
                      'proposal_digest':row['digest'], 'review':approval,
                      'tool_calls':row['call_count']+1, 'elapsed_seconds':time.monotonic()-start}
            with self.connect() as db:
                db.execute("UPDATE proposals SET status='completed',report=? WHERE id=?", (json.dumps(result), workflow_id))
                self._event(db, workflow_id, 'tool_completed', {'role':'evaluator', 'outcome_hash':report.outcome_hash,
                             'evaluation_passed':report.evaluation_passed, 'elapsed_seconds':result['elapsed_seconds']})
        except Exception as exc:
            with self.connect() as db:
                db.execute("UPDATE proposals SET status='failed',error=? WHERE id=?", (str(exc), workflow_id))
                self._event(db, workflow_id, 'tool_failed', {'error_type':type(exc).__name__, 'message':str(exc),
                             'elapsed_seconds':time.monotonic()-start, 'automatic_retry':False})
            self.export(workflow_id)
            raise
        self.export(workflow_id)
        return result

    @staticmethod
    def _invoke(command, log_path, timeout):
        with log_path.open('wb') as log:
            process = subprocess.Popen(command, cwd=Path(__file__).resolve().parents[2],
                                       stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                return process.wait(timeout)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
                raise WorkflowError('Experiment tool timed out; process group terminated')

    def get(self, workflow_id):
        with self.connect() as db:
            row = dict(self._row(db, workflow_id))
            events = db.execute('SELECT sequence,time,event,payload FROM workflow_events WHERE workflow_id=? ORDER BY sequence',
                                (workflow_id,)).fetchall()
        for name in ('body', 'policy', 'approval', 'report'):
            row[name] = json.loads(row[name]) if row[name] else None
        row['events'] = [{**dict(e), 'payload':json.loads(e['payload'])} for e in events]
        return row

    def export(self, workflow_id):
        directory = self.root / workflow_id; directory.mkdir(exist_ok=True)
        path = directory / 'workflow.json'
        path.write_text(json.dumps(self.get(workflow_id), indent=2) + '\n')
        return path
