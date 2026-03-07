"""FastAPI application entrypoint."""

from fastapi import FastAPI

from backend.api.routes.missions import router as missions_router
from backend.core.logging import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="AutonomyOS",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.get("/")
def root() -> dict[str, str]:
    """Service availability check."""
    return {"service": "AutonomyOS", "status": "running"}


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness/readiness probe."""
    return {"status": "ok"}


app.include_router(missions_router)
