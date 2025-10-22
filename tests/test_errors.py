from __future__ import annotations

from typing import Any, Dict

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def assert_problem(response, *, status: int, code: str) -> Dict[str, Any]:
    body = response.json()
    assert response.status_code == status
    assert body["status"] == status
    assert body["code"] == code
    assert body["type"].startswith("https://ideacatalog.app/problems/")
    assert body["title"]
    assert body["detail"]
    assert body["correlation_id"]
    return body


def test_idea_not_found_returns_problem_details():
    response = client.get("/ideas/999")
    body = assert_problem(response, status=404, code="idea_not_found")
    assert body["detail"] == "idea not found"


def test_invalid_status_change_uses_problem_details():
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
    body = assert_problem(update_resp, status=422, code="invalid_status")
    assert "unsupported status" in body["detail"]


def test_evaluate_missing_idea_exposes_problem_details():
    resp = client.post(
        "/ideas/42/evaluations",
        json={"value": 5, "effort": 3, "confidence": 7},
    )
    assert_problem(resp, status=404, code="idea_not_found")


def test_rate_limit_blocks_excessive_requests(monkeypatch):
    monkeypatch.setenv("IDEA_RATE_LIMIT_PER_MINUTE", "2")
    base_payload = {
        "title": "Idea ",
        "description": "Some useful description for rate limit testing.",
        "tags": ["rl"],
    }

    headers = {"X-Client-Id": "tester"}

    for idx in range(2):
        payload = dict(base_payload)
        payload["title"] = f"Idea {idx}"
        resp = client.post("/ideas", json=payload, headers=headers)
        assert resp.status_code == 201

    third_payload = dict(base_payload)
    third_payload["title"] = "Idea overflow"
    third = client.post("/ideas", json=third_payload, headers=headers)
    body = assert_problem(third, status=429, code="too_many_requests")
    assert body["limit_per_minute"] == 2
