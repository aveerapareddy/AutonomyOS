"""Telemetry endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.dependencies import get_mission_service, get_telemetry_service
from backend.schemas.telemetry import TelemetryQueryResponse
from backend.services.mission_service import MissionService
from backend.services.telemetry_service import TelemetryService

router = APIRouter(prefix="/missions", tags=["telemetry"])


@router.get("/{mission_id}/telemetry", response_model=TelemetryQueryResponse)
def get_mission_telemetry(
    mission_id: str,
    after_sequence: int = Query(default=0, ge=0),
    mission_service: MissionService = Depends(get_mission_service),
    telemetry_service: TelemetryService = Depends(get_telemetry_service),
) -> TelemetryQueryResponse:
    """Return ordered event timeline for a mission. 404 if mission does not exist."""
    if mission_service.get(mission_id) is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    events = [e for e in telemetry_service.get_events_for_mission(mission_id) if e.sequence > after_sequence]
    return TelemetryQueryResponse(mission_id=mission_id, events=events, count=len(events))


# Bounded SSE tail with Last-Event-ID reconnect support. Durable state stays in the journal.
import asyncio
import json
import time
from fastapi import Header,Request
from starlette.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool
from threading import Lock
_stream_lock=Lock()
_stream_count=0

@router.get('/{mission_id}/stream')
async def stream_mission(
    mission_id:str,request:Request,after_sequence:int=Query(default=0,ge=0),
    await_new_run:bool=False,
    last_event_id:str|None=Header(default=None),
    mission_service:MissionService=Depends(get_mission_service),
    telemetry_service:TelemetryService=Depends(get_telemetry_service),
):
    global _stream_count
    if mission_service.get(mission_id) is None:raise HTTPException(404,'Mission not found')
    try:cursor=max(after_sequence,int(last_event_id or 0))
    except ValueError:raise HTTPException(422,'Last-Event-ID must be a nonnegative sequence')
    if cursor<0:raise HTTPException(422,'Last-Event-ID must be nonnegative')
    initial_cursor=cursor
    with _stream_lock:
        if _stream_count>=20:raise HTTPException(429,'Too many telemetry streams',headers={'Retry-After':'5'})
        _stream_count+=1
    async def events():
        global _stream_count
        nonlocal cursor
        started=time.monotonic();heartbeat=0
        try:
            while time.monotonic()-started<25:
                if await request.is_disconnected():break
                records=await run_in_threadpool(telemetry_service.get_events_for_mission,mission_id)
                for record in records:
                    if record.sequence<=cursor:continue
                    cursor=record.sequence
                    yield f'id: {cursor}\nevent: telemetry\ndata: {record.model_dump_json()}\n\n'
                if records and records[-1].event_type in {'mission_completed','mission_failed'} and (not await_new_run or records[-1].sequence>initial_cursor):
                    yield 'event: terminal\ndata: {"complete":true}\n\n';break
                now=time.monotonic()
                if now-heartbeat>3:
                    yield ': heartbeat\n\n';heartbeat=now
                await asyncio.sleep(.1)
        finally:
            with _stream_lock:_stream_count-=1
    return StreamingResponse(events(),media_type='text/event-stream',headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})
