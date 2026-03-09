"""Benchmark endpoints."""

from fastapi import APIRouter, Depends

from backend.api.dependencies import get_benchmark_service
from backend.schemas.benchmark import BenchmarkRunRequest, BenchmarkSummary
from backend.services.benchmark_service import BenchmarkService

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])


@router.post("/run", response_model=BenchmarkSummary)
def run_benchmark(
    body: BenchmarkRunRequest,
    benchmark_service: BenchmarkService = Depends(get_benchmark_service),
) -> BenchmarkSummary:
    """Run benchmark: generate scenarios, execute pipeline per scenario, return summary."""
    return benchmark_service.run(body)
