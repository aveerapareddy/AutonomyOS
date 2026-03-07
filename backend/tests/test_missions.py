"""Mission API tests."""

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app

client = TestClient(app)


def test_create_mission_success() -> None:
    """POST /missions with valid body returns 201 and mission id."""
    response = client.post(
        "/missions",
        json={"mission_text": "Navigate to the red cube", "world_id": "warehouse_01"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "mission_id" in data
    assert len(data["mission_id"]) == 32
    assert data["status"] == "received"
    assert "created_at" in data


def test_create_mission_blank_text_rejected() -> None:
    """POST /missions with blank mission_text returns 422."""
    response = client.post("/missions", json={"mission_text": "   "})
    assert response.status_code == 422


def test_create_mission_empty_text_rejected() -> None:
    """POST /missions with empty mission_text returns 422."""
    response = client.post("/missions", json={"mission_text": ""})
    assert response.status_code == 422


def test_get_mission_found() -> None:
    """GET /missions/{id} returns full record for existing mission."""
    create_resp = client.post(
        "/missions",
        json={"mission_text": "Pick up the box", "world_id": "test_world"},
    )
    assert create_resp.status_code == 201
    mission_id = create_resp.json()["mission_id"]

    get_resp = client.get(f"/missions/{mission_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["mission_id"] == mission_id
    assert data["mission_text"] == "Pick up the box"
    assert data["world_id"] == "test_world"
    assert data["status"] == "received"
    assert "created_at" in data


def test_get_mission_not_found() -> None:
    """GET /missions/{id} returns 404 for unknown id."""
    response = client.get("/missions/nonexistent_id_12345")
    assert response.status_code == 404
    assert response.json()["detail"] == "Mission not found"
