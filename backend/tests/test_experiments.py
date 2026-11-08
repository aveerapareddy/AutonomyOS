import json
import pytest
from pydantic import ValidationError
from backend.experiments.ledger import Ledger
from backend.experiments.models import ExperimentRequest
from backend.experiments.runner import compare_reports, run_experiment


def test_request_bounds():
    for args in ({"scenario_count": 101}, {"seed": -1}, {"minimum_success_rate": float("nan")}, {"tool": "shell"}):
        with pytest.raises(ValidationError):
            ExperimentRequest(**args)


def test_real_repeat_and_restart(tmp_path):
    ledger = Ledger(tmp_path / "runs.sqlite")
    request = ExperimentRequest(scenario_count=2, seed=42, minimum_success_rate=0)
    a = run_experiment(request, ledger, tmp_path / "a")
    b = run_experiment(request, ledger, tmp_path / "b")
    assert a.status == b.status == "completed"
    assert compare_reports(a.model_dump(), b.model_dump())["reproduced"]
    durable = Ledger(tmp_path / "runs.sqlite").read(a.run_id)
    assert durable["report"]["outcome_hash"] == a.outcome_hash
    assert [e["sequence"] for e in durable["events"]] == list(range(1, 5))
    assert durable["status"] == "completed"
    assert json.loads((tmp_path / "a/mission-traces.json").read_text())
    assert a.summary["inference_cost_usd"] is None
    assert not a.summary["collision_safety_evaluated"]


def test_tool_error_is_durable(tmp_path, monkeypatch):
    import backend.experiments.runner as runner
    def fail(*args, **kwargs):
        raise RuntimeError("injected simulator outage")
    monkeypatch.setattr(runner, "run_benchmark", fail)
    with pytest.raises(RuntimeError, match="outage"):
        run_experiment(ExperimentRequest(), Ledger(tmp_path / "runs.sqlite"), tmp_path / "out")
    state = json.loads((tmp_path / "out/workflow.json").read_text())
    assert state["status"] == "failed"
    assert state["report"] is None
    assert state["events"][-1]["payload"]["failed_stage"] == "simulation"


def test_report_comparison_rejects_changed_scenarios(tmp_path):
    ledger = Ledger(tmp_path / "runs.sqlite")
    a = run_experiment(ExperimentRequest(scenario_count=1, seed=42), ledger, tmp_path / "a").model_dump()
    b = run_experiment(ExperimentRequest(scenario_count=1, seed=43), ledger, tmp_path / "b").model_dump()
    assert not compare_reports(a, b)["reproduced"]


def test_missing_simulator_does_not_pass(tmp_path, monkeypatch):
    import backend.services.orchestrator_service as orchestrator
    def unavailable(*args, **kwargs):
        raise ImportError("simulator missing")
    monkeypatch.setattr(orchestrator, "run_sim_execution", unavailable)
    result = run_experiment(ExperimentRequest(scenario_count=1, seed=42, minimum_success_rate=0),
                            Ledger(tmp_path / "ledger.sqlite"), tmp_path / "run")
    assert result.status == "failed"
    assert not result.evaluation_passed


def test_reference_dataset_runs_real_simulator():
    from pathlib import Path
    from scripts.run_evaluation_suite import evaluate
    path = Path(__file__).resolve().parents[2] / "evaluation/reference.json"
    result = evaluate(path)
    assert result["passed"]
    assert result["total_cases"] == 4
    assert result["matched_cases"] == 4
    assert result["cases"][0]["result"]["simulator_steps"] > 0
