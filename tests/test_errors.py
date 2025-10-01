import pytest
from fastapi.testclient import TestClient

from app.main import app, storage


@pytest.fixture(autouse=True)
def reset_storage():
    storage.clear()
    yield
    storage.clear()


client = TestClient(app)


def test_idea_not_found():
    response = client.get("/ideas/999")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "idea_not_found"


def test_invalid_status_change():
    create_resp = client.post(
        "/ideas",
        json={
            "title": "Test idea",
            "description": "A description that is definitely long enough.",
            "tags": ["test"],
        },
    )
    assert create_resp.status_code == 201
    idea_id = create_resp.json()["id"]

    update_resp = client.patch(
        f"/ideas/{idea_id}",
        json={"status": "invalid"},
    )
    assert update_resp.status_code == 422
    assert update_resp.json()["error"]["code"] == "invalid_status"


def test_evaluate_missing_idea():
    resp = client.post(
        "/ideas/42/evaluations",
        json={"value": 5, "effort": 3, "confidence": 7},
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "idea_not_found"
