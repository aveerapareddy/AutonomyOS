"""Orchestrates benchmark: generate scenarios, run runner, return summary. In-memory only."""

import uuid

from backend.schemas.benchmark import BenchmarkRunRequest, BenchmarkSummary
from backend.scenarios.benchmark_runner import run_benchmark
from backend.scenarios.generator import generate_scenarios
from backend.scenarios.scenario_config import ScenarioConfig
from backend.services.mission_service import MissionService
from backend.services.telemetry_service import TelemetryService


class BenchmarkService:
    """Runs benchmarks: scenario generation + benchmark runner. No persistence."""

    def __init__(
        self,
        mission_service: MissionService,
        telemetry_service: TelemetryService,
    ) -> None:
        self._mission_service = mission_service
        self._telemetry_service = telemetry_service

    def run(self, request: BenchmarkRunRequest) -> BenchmarkSummary:
        """Generate scenarios, run benchmark, return summary."""
        scenario_count = max(1, min(request.scenario_count, 100))
        scenarios = generate_scenarios(
            count=scenario_count,
            seed=request.seed,
        )
        benchmark_id = uuid.uuid4().hex
        return run_benchmark(
            scenario_configs=scenarios,
            mission_service=self._mission_service,
            telemetry_service=self._telemetry_service,
            benchmark_id=benchmark_id,
            benchmark_name=request.benchmark_name,
        )
