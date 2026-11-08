"""Authenticated operations; simulations use a separate isolated worker consumer."""
from pathlib import Path
import json
import subprocess
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException,Request
from pydantic import BaseModel,ConfigDict,Field
from backend.api.auth import Principal,authenticate
from backend.api.routes.workflows import call
from backend.core.config import get_settings
from backend.operations.jobs import JobStore,JobRequest
from backend.operations.site import SiteSpec,OccupancyImport
from backend.knowledge.answers import answer
from backend.knowledge.graph import build_graph

router=APIRouter(prefix='/operations',tags=['operations'])

def store(principal:Principal=Depends(authenticate)):
    principal.require('read');path=get_settings().operations_directory
    if not path:raise HTTPException(403,'Operations directory is not configured')
    return JobStore(Path(path))

@router.get('/identity')
def identity(principal:Principal=Depends(authenticate)):
    return {'name':principal.name,'roles':sorted(principal.roles),'individual_subject':principal.individual}

@router.get('/jobs')
def listing(jobs:JobStore=Depends(store)):return jobs.list()

class Submission(BaseModel):
    model_config=ConfigDict(extra='forbid')
    key:str=Field(min_length=8,max_length=80)
    request:JobRequest

@router.post('/jobs',status_code=202)
def submit(body:Submission,jobs:JobStore=Depends(store),principal:Principal=Depends(authenticate)):
    principal.require('execute');return call(lambda:jobs.submit(body.request,body.key))

@router.get('/jobs/{ident}')
def get(ident:str,jobs:JobStore=Depends(store)):return call(lambda:jobs.get(ident))

@router.post('/jobs/{ident}/cancel')
def cancel(ident:str,jobs:JobStore=Depends(store),principal:Principal=Depends(authenticate)):
    principal.require('execute');return call(lambda:jobs.cancel(ident))

@router.post('/site/validate')
def validate(site:SiteSpec,principal:Principal=Depends(authenticate)):
    principal.require('read');return {'site':site.model_dump(mode='json'),'scenario':site.scenario().model_dump(mode='json')}

@router.post('/site/occupancy')
def occupancy(body:OccupancyImport,principal:Principal=Depends(authenticate)):
    principal.require('read');return call(lambda:body.to_site().model_dump(mode='json'))

class Question(BaseModel):
    model_config=ConfigDict(extra='forbid')
    question:str=Field(min_length=1,max_length=2000)
    method:Literal['lexical','semantic']='lexical'

@router.post('/knowledge')
def knowledge(body:Question,principal:Principal=Depends(authenticate)):
    principal.require('read')
    root=Path(__file__).resolve().parents[3]
    if body.method=='semantic':
        settings=get_settings()
        if not settings.semantic_python or not settings.semantic_index:raise HTTPException(503,'Semantic retrieval is not configured; select extractive retrieval')
        try:
            process=subprocess.run([settings.semantic_python,'-m','scripts.semantic_retrieval','--index',settings.semantic_index,'--question',body.question],cwd=root,capture_output=True,text=True,timeout=30)
            if process.returncode:raise HTTPException(503,'Semantic retrieval failed; inspect server model/cache configuration')
            return json.loads(process.stdout)
        except subprocess.TimeoutExpired:raise HTTPException(504,'Semantic retrieval timed out')
    return call(lambda:answer(root,body.question))

@router.get('/graph')
def graph(jobs:JobStore=Depends(store)):return build_graph(jobs)

@router.get('/metrics')
def metrics(request:Request,principal:Principal=Depends(authenticate)):
    principal.require('read')
    from backend.core.observability import TelemetryMiddleware
    layer=request.app.middleware_stack
    while layer and not isinstance(layer,TelemetryMiddleware):layer=getattr(layer,'app',None)
    if not layer:return {'routes':{}}
    with layer.lock:return {'routes':{k:dict(v) for k,v in layer.routes.items()}}
