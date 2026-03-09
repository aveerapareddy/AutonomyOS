"""Scenario generator and benchmark tests."""

from fastapi.testclient import TestClient

from backend.api.main import app
from backend.scenarios.generator import generate_scenarios

client = TestClient(app)


def test_scenario_generation_deterministic_with_seed() -> None:
    """Same seed produces same scenario configs."""
    a = generate_scenarios(count=3, seed=42)
    b = generate_scenarios(count=3, seed=42)
    assert len(a) == 3 and len(b) == 3
    for i in range(3):
        assert a[i].scenario_id == b[i].scenario_id
        assert a[i].obstacle_positions == b[i].obstacle_positions
        assert a[i].target_position == b[i].target_position


def test_scenario_generation_different_seeds_differ() -> None:
    """Different seeds produce different configs (with high probability)."""
    a = generate_scenarios(count=2, seed=1)
    b = generate_scenarios(count=2, seed=2)
    assert a[0].scenario_id != b[0].scenario_id or a[0].target_position != b[0].target_position


def test_benchmark_summary_aggregates_correctly() -> None:
    """Benchmark run returns summary with correct totals and averages."""
    resp = client.post(
        "/benchmarks/run",
        json={"benchmark_name": "agg_test", "scenario_count": 2, "seed": 123},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["benchmark_name"] == "agg_test"
    assert data["total_scenarios"] == 2
    assert data["success_count"] + data["failure_count"] == 2
    assert 0 <= data["success_rate"] <= 1.0
    assert data["average_waypoint_count"] >= 0
    assert data["average_execution_steps"] >= 0
    assert len(data["scenario_results"]) == 2


def test_benchmark_invalid_scenario_count_rejected() -> None:
    """scenario_count 0 or negative returns 422."""
    resp = client.post(
        "/benchmarks/run",
        json={"benchmark_name": "x", "scenario_count": 0},
    )
    assert resp.status_code == 422


def test_benchmark_per_scenario_results_returned() -> None:
    """Each scenario has a result record with expected fields."""
    resp = client.post(
        "/benchmarks/run",
        json={"benchmark_name": "per_scenario", "scenario_count": 1, "seed": 999},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["scenario_results"]) == 1
    r = data["scenario_results"][0]
    assert "scenario_id" in r
    assert "scenario_name" in r
    assert "robot_start_position" in r
    assert "target_position" in r
    assert "success" in r
    assert "path_found" in r
    assert "waypoint_count" in r
    assert "execution_steps" in r


def test_benchmark_scenario_robot_start_honored() -> None:
    """Scenario results include scenario_name, robot_start_position, target_position from config."""
    scenarios = generate_scenarios(count=2, seed=42)
    resp = client.post(
        "/benchmarks/run",
        json={"benchmark_name": "start_test", "scenario_count": 2, "seed": 42},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["scenario_results"]) == 2
    for i, r in enumerate(data["scenario_results"]):
        assert r["scenario_name"] == scenarios[i].scenario_name
        assert r["robot_start_position"] == list(scenarios[i].robot_start_position)
        assert r["target_position"] == list(scenarios[i].target_position)
