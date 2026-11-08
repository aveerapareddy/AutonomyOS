"""Opt-in operator API. Imported model reports are not live inference calls."""
import hmac
import json
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from backend.core.config import get_settings
from backend.experiments.agent_workflow import AgentWorkflow, WorkflowError, WorkflowPolicy
from backend.api.simulation_gate import simulation_slot
from backend.api.auth import Principal, authenticate

router=APIRouter(prefix='/workflows',tags=['operator workflows'])


def operator(principal: Principal = Depends(authenticate)) -> AgentWorkflow:
    settings=get_settings()
    if settings.public_demo or not settings.workflow_directory:
        raise HTTPException(403,'Operator workflows are not enabled')
    principal.require('read')
    return AgentWorkflow(Path(settings.workflow_directory),WorkflowPolicy(max_scenarios=10))


class Review(BaseModel):
    model_config=ConfigDict(extra='forbid')
    digest: str = Field(pattern=r'^[0-9a-f]{64}$')
    actor: str = Field(min_length=1,max_length=100)


class Rejection(BaseModel):
    model_config=ConfigDict(extra='forbid')
    actor: str = Field(min_length=1,max_length=100)
    reason: str = Field(min_length=1,max_length=500)


def call(operation):
    try:
        return operation()
    except (WorkflowError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(422,str(exc)) from exc


@router.get('')
def listing(workflow: AgentWorkflow=Depends(operator)):
    with workflow.connect() as db:
        rows=db.execute('SELECT id,status,digest,created_at FROM proposals ORDER BY created_at DESC LIMIT 50').fetchall()
    return [dict(row) for row in rows]


@router.post('/import',status_code=201)
async def import_report(request: Request, workflow: AgentWorkflow=Depends(operator), principal: Principal=Depends(authenticate)):
    principal.require('execute')
    chunks=[];length=0
    async for chunk in request.stream():
        length+=len(chunk)
        if length>256000:
            raise HTTPException(413,'Inference report exceeds 256 KB')
        chunks.append(chunk)
    raw=b''.join(chunks)
    # Named server-owned file; no client-selected filesystem path.
    with tempfile.TemporaryDirectory(dir=workflow.root) as directory:
        path=Path(directory)/'inference.json';path.write_bytes(raw)
        return call(lambda: workflow.submit_inference(path))


@router.get('/{ident}')
def get(ident: str,workflow: AgentWorkflow=Depends(operator)):
    return call(lambda:workflow.get(ident))


@router.post('/{ident}/approve')
def approve(ident: str,body: Review,workflow: AgentWorkflow=Depends(operator),principal: Principal=Depends(authenticate)):
    principal.require('review')
    return call(lambda:workflow.approve(ident,body.digest,principal.name if principal.individual else body.actor,'human'))


@router.post('/{ident}/reject')
def reject(ident: str,body: Rejection,workflow: AgentWorkflow=Depends(operator),principal: Principal=Depends(authenticate)):
    principal.require('review')
    call(lambda:workflow.reject(ident,principal.name if principal.individual else body.actor,body.reason))
    return workflow.get(ident)


@router.post('/{ident}/execute')
def execute(ident: str,workflow: AgentWorkflow=Depends(operator),principal: Principal=Depends(authenticate)):
    principal.require('execute')
    with simulation_slot():
        call(lambda:workflow.execute(ident))
    return workflow.get(ident)
