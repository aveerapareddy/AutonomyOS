"""FastAPI application entrypoint."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from backend.core.config import get_settings
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes.workflows import router as workflows_router
from backend.api.routes.benchmarks import router as benchmarks_router
from backend.api.routes.missions import router as missions_router
from backend.api.routes.replay import router as replay_router
from backend.api.routes.telemetry import router as telemetry_router
from backend.core.logging import get_logger
from backend.api.demo_guard import DemoGuard

logger = get_logger(__name__)

app = FastAPI(
    title="AutonomyOS",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(DemoGuard, public_demo=get_settings().public_demo)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, str]:
    """Service availability check."""
    return {"service": "AutonomyOS", "status": "running"}


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness/readiness probe."""
    return {"status": "ok"}


app.include_router(workflows_router)
app.include_router(missions_router)
app.include_router(telemetry_router)
app.include_router(replay_router)
app.include_router(benchmarks_router)


# Optional same-origin production bundle; API root and health endpoints remain intact.
if get_settings().frontend_directory:
    app.mount("/demo", StaticFiles(directory=get_settings().frontend_directory, html=True), name="dashboard")
