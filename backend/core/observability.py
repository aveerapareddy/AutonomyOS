"""OpenTelemetry request spans and bounded local metrics; no request bodies or tokens."""
import json
from pathlib import Path
import re
from threading import Lock
import time
from starlette.middleware.base import BaseHTTPMiddleware
from opentelemetry import trace
from opentelemetry.trace import Status,StatusCode
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor,SpanExporter,SpanExportResult

class JsonSpanExporter(SpanExporter):
    def __init__(self,directory):
        self.path=Path(directory)/'http-spans.jsonl';self.path.parent.mkdir(parents=True,exist_ok=True);self.lock=Lock()
    def export(self,spans):
        with self.lock:
            # Bound a local run to 20 MB; callers rotate/export between demo sessions.
            if self.path.exists() and self.path.stat().st_size>20_000_000:return SpanExportResult.FAILURE
            with self.path.open('a') as f:
                for s in spans:
                    f.write(json.dumps({'trace_id':f'{s.context.trace_id:032x}','span_id':f'{s.context.span_id:016x}',
                     'parent_span_id':f'{s.parent.span_id:016x}' if s.parent else None,'name':s.name,
                     'start_time':s.start_time,'end_time':s.end_time,'status':s.status.status_code.name,
                     'attributes':dict(s.attributes)})+'\n')
        return SpanExportResult.SUCCESS

class TelemetryMiddleware(BaseHTTPMiddleware):
    def __init__(self,app,directory=''):
        super().__init__(app);self.lock=Lock();self.routes={}
        self.provider=TracerProvider()
        if directory:self.provider.add_span_processor(SimpleSpanProcessor(JsonSpanExporter(directory)))
        self.tracer=self.provider.get_tracer('autonomyos.http','2.0')
    async def dispatch(self,request,call_next):
        route=re.sub(r'[0-9a-f]{32}','{id}',request.url.path)
        if route.startswith('/demo'):route='/demo/assets'
        if len(route)>100 or not route.startswith(('/missions','/operations','/workflows','/health','/metrics','/demo','/benchmarks','/docs','/openapi','/redoc')):route='/other'
        name=request.method+' '+route;start=time.monotonic();status=500
        with self.tracer.start_as_current_span(name) as span:
            request.state.trace_id=f'{span.get_span_context().trace_id:032x}'
            span.set_attribute('http.request.method',request.method);span.set_attribute('http.route',route)
            try:
                response=await call_next(request);status=response.status_code
                response.headers['X-Trace-ID']=f'{span.get_span_context().trace_id:032x}'
                return response
            finally:
                elapsed=time.monotonic()-start;span.set_attribute('http.response.status_code',status)
                if status>=500:span.set_status(Status(StatusCode.ERROR))
                with self.lock:
                    if name not in self.routes and len(self.routes)>=100:name='OTHER'
                    metric=self.routes.setdefault(name,{'requests':0,'errors':0,'denials':0,'duration_seconds':0.,'maximum_seconds':0.})
                    metric['requests']+=1;metric['errors']+=int(status>=500);metric['denials']+=int(status in {401,403});metric['duration_seconds']+=elapsed
                    metric['maximum_seconds']=max(metric['maximum_seconds'],elapsed)
