"""Bounded anonymous CPU demo policy; not a substitute for a deployment gateway."""
import asyncio
import logging
import time
import uuid
from collections import deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger('autonomy.http')


class DemoGuard(BaseHTTPMiddleware):
    def __init__(self, app, public_demo=False):
        super().__init__(app)
        self.public_demo = public_demo
        self.executing = asyncio.Lock()
        self.creations = deque()

    async def dispatch(self, request, call_next):
        request_id = uuid.uuid4().hex
        start = time.monotonic()
        path = request.url.path
        is_execution = request.method == 'POST' and path.endswith('/execute')
        acquired = False
        if self.public_demo:
            if path.startswith('/benchmarks'):
                return JSONResponse({'detail': 'Batch benchmarks are disabled on the public demo'}, status_code=403)
            try:
                if int(request.headers.get('content-length', '0')) > 16384:
                    return JSONResponse({'detail': 'Request too large'}, status_code=413)
            except ValueError:
                return JSONResponse({'detail': 'Invalid content length'}, status_code=400)
            if request.method == 'POST' and path == '/missions':
                now = time.monotonic()
                while self.creations and now - self.creations[0] > 60:
                    self.creations.popleft()
                if len(self.creations) >= 20:
                    return JSONResponse({'detail': 'Demo busy; retry in a minute'}, status_code=429, headers={'Retry-After': '60'})
                self.creations.append(now)
            if is_execution:
                if self.executing.locked():
                    return JSONResponse({'detail': 'A simulation is already running'}, status_code=429, headers={'Retry-After': '5'})
                await self.executing.acquire()
                acquired = True
        try:
            response = await call_next(request)
        finally:
            if acquired:
                self.executing.release()
        response.headers['X-Request-ID'] = request_id
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['X-Frame-Options'] = 'DENY'
        logger.info('request_id=%s method=%s status=%s duration_ms=%.1f', request_id, request.method, response.status_code, (time.monotonic()-start)*1000)
        return response
