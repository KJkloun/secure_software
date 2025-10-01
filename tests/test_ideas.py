import pytest
from fastapi.testclient import TestClient

from app.main import app, storage


@pytest.fixture(autouse=True)
def reset_storage():
    storage.clear()
    yield
    storage.clear()


def create_sample_idea(client, **override):
    payload = {
        "title": "AI assistant for feedback",
        "description": "Collect internal feedback and suggest improvements automatically.",
        "tags": ["ai", "feedback"],
    }
    payload.update(override)
    response = client.post("/ideas", json=payload)
    assert response.status_code == 201
    return response.json()


def test_create_and_get_idea():
    client = TestClient(app)

    created = create_sample_idea(client)

    assert created["status"] == "draft"
    assert created["score"] == {
        "value": None,
        "confidence": None,
        "effort": None,
        "impact": None,
        "votes": 0,
    }

    idea_id = created["id"]
    fetched = client.get(f"/ideas/{idea_id}")
    assert fetched.status_code == 200
    assert fetched.json()["title"] == created["title"]


def test_list_ideas_with_filters():
    client = TestClient(app)

    idea_low = create_sample_idea(client, title="Idea low")
    idea_high = create_sample_idea(client, title="Idea high", tags=["ai", "ops"])

    client.post(
        f"/ideas/{idea_low['id']}/evaluations",
        json={"value": 3, "effort": 5, "confidence": 4},
    )
    client.post(
        f"/ideas/{idea_high['id']}/evaluations",
        json={"value": 8, "effort": 3, "confidence": 9},
    )

    all_items = client.get("/ideas")
    assert all_items.status_code == 200
    assert len(all_items.json()) == 2

    filtered = client.get("/ideas", params={"min_score": 6})
    assert filtered.status_code == 200
    bodies = filtered.json()
    assert len(bodies) == 1
    assert bodies[0]["id"] == idea_high["id"]

    tag_filtered = client.get("/ideas", params={"tag": "ops"})
    assert tag_filtered.status_code == 200
    assert len(tag_filtered.json()) == 1
    assert tag_filtered.json()[0]["id"] == idea_high["id"]


def test_update_idea():
    client = TestClient(app)
    created = create_sample_idea(client)

    idea_id = created["id"]
    update_response = client.patch(
        f"/ideas/{idea_id}",
        json={"status": "in_review", "tags": ["ai", "product"]},
    )
    assert update_response.status_code == 200
    body = update_response.json()
    assert body["status"] == "in_review"
    assert body["tags"] == ["ai", "product"]


def test_evaluation_updates_score():
    client = TestClient(app)
    created = create_sample_idea(client)
    idea_id = created["id"]

    first = client.post(
        f"/ideas/{idea_id}/evaluations",
        json={"value": 6, "effort": 4, "confidence": 7, "comment": "solid"},
    )
    assert first.status_code == 200
    assert first.json()["score"]["votes"] == 1

    second = client.post(
        f"/ideas/{idea_id}/evaluations",
        json={"value": 9, "effort": 3, "confidence": 8},
    )
    assert second.status_code == 200
    score = second.json()["score"]
    assert score["votes"] == 2
    assert score["value"] == pytest.approx(7.5)
    assert score["effort"] == pytest.approx(3.5)
    assert score["impact"] == pytest.approx((7.5 * 7.5) / 3.5, rel=1e-2)

    evaluations = client.get(f"/ideas/{idea_id}/evaluations")
    assert evaluations.status_code == 200
    assert len(evaluations.json()) == 2
