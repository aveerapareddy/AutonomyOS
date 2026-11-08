import json
import httpx
import pytest
from pydantic import ValidationError
from backend.integrations.nim import NimPlanner, proposal_hash, require_approval
from backend.experiments.models import ExperimentRequest
from backend.scenarios.generator import generate_scenarios


def test_nim_protocol_contract_only():
    def handler(request):
        assert str(request.url) == "https://example.test/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer test-secret"
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({"seed": 8, "scenario_count": 3})}}]})
    proposal = NimPlanner("https://example.test/v1", "test-model", "test-secret",
                          httpx.MockTransport(handler)).propose("Try three cases")
    assert proposal.scenario_count == 3
    require_approval(proposal, proposal_hash(proposal))
    with pytest.raises(ValueError):
        require_approval(proposal.model_copy(update={"scenario_count": 4}), proposal_hash(proposal))


def test_nim_rejects_unbounded_model_output():
    transport = httpx.MockTransport(lambda r: httpx.Response(200, json={"choices": [{"message": {"content": '{"scenario_count":100000}'}}]}))
    with pytest.raises(ValidationError):
        NimPlanner("https://example.test/v1", "test", transport=transport).propose("many")


def test_nim_does_not_follow_redirects():
    transport = httpx.MockTransport(lambda r: httpx.Response(302, headers={"location": "https://other.test"}))
    with pytest.raises(httpx.HTTPStatusError):
        NimPlanner("https://example.test/v1", "test", transport=transport).propose("one")


def test_real_openusd_roundtrip(tmp_path):
    pytest.importorskip("pxr")
    from pxr import Usd, UsdGeom
    from backend.integrations.openusd import export_scenario
    scenario = generate_scenarios(1, 42)[0]
    path = export_scenario(scenario, tmp_path / "world.usda")
    stage = Usd.Stage.Open(str(path))
    assert UsdGeom.GetStageUpAxis(stage) == "Z"
    assert UsdGeom.GetStageMetersPerUnit(stage) == 1.0
    assert stage.GetDefaultPrim().GetAttribute("autonomyos:scenarioId").Get() == scenario.scenario_id
    target = UsdGeom.Xformable(stage.GetPrimAtPath("/World/target"))
    position = target.ComputeLocalToWorldTransform(Usd.TimeCode.Default()).ExtractTranslation()
    assert tuple(position) == pytest.approx((*scenario.target_position, .15))
    for i, (x, y) in enumerate(scenario.obstacle_positions):
        prim = stage.GetPrimAtPath(f"/World/obstacle_{i}")
        assert prim.IsA(UsdGeom.Cube)
        transform = UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
        assert tuple(transform.ExtractTranslation()) == pytest.approx((x, y, .5))
    robot = UsdGeom.Xformable(stage.GetPrimAtPath("/World/robot"))
    matrix = robot.ComputeLocalToWorldTransform(Usd.TimeCode.Default())
    assert tuple(matrix.ExtractTranslation()) == pytest.approx((*scenario.robot_start_position[:2], .1))


def test_huggingface_proposal_validation():
    from backend.integrations.huggingface import validate_proposal
    assert validate_proposal('```json\n{"seed":42,"scenario_count":5}\n```').seed == 42
    for raw in ('{"scenario_count":10000}', '{"command":"rm -rf"}', 'not JSON'):
        with pytest.raises(ValueError):
            validate_proposal(raw)
