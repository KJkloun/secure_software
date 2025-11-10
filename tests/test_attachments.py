from __future__ import annotations

from typing import Any, Dict

from fastapi.testclient import TestClient

from app.main import app, attachment_storage, storage
from app.problem_details import ApiProblem
from app.security import MAX_ATTACHMENT_BYTES

client = TestClient(app)


def expect_problem(response, *, status: int, code: str) -> Dict[str, Any]:
    body = response.json()
    assert response.status_code == status
    assert body["status"] == status
    assert body["code"] == code
    assert body["correlation_id"]
    return body


def make_png(payload: bytes = b"payload") -> bytes:
    return b"\x89PNG\r\n\x1a\n" + payload


def test_upload_accepts_png_and_records_attachment():
    create = client.post(
        "/ideas",
        json={
            "title": "Attachment idea",
            "description": "Idea that needs a screenshot.",
            "tags": ["files"],
        },
    )
    assert create.status_code == 201
    idea = create.json()

    data = make_png(b"\x00" * 128)
    response = client.post(
        f"/ideas/{idea['id']}/attachments",
        files={"file": ("diagram.png", data, "image/png")},
    )
    body = response.json()
    assert response.status_code == 201
    assert body["content_type"] == "image/png"
    attachment_id = body["attachment_id"]
    assert attachment_id.endswith(".png")
    assert attachment_id != "diagram.png"
    assert attachment_id in body["attachments"]

    stored_path = attachment_storage.base_dir / attachment_id
    assert stored_path.exists()
    assert stored_path.read_bytes().startswith(b"\x89PNG")

    idea_state = client.get(f"/ideas/{idea['id']}").json()
    assert attachment_id in idea_state["attachments"]


def test_rejects_large_attachment():
    create = client.post(
        "/ideas",
        json={
            "title": "Big file idea",
            "description": "Idea that tries to upload a huge file.",
            "tags": ["files"],
        },
    )
    assert create.status_code == 201
    idea = create.json()

    huge_data = make_png(b"a" * (MAX_ATTACHMENT_BYTES + 1))
    resp = client.post(
        f"/ideas/{idea['id']}/attachments",
        files={"file": ("huge.png", huge_data, "image/png")},
    )
    body = expect_problem(resp, status=413, code="attachment_too_large")
    assert "size limit" in body["detail"]


def test_rejects_unknown_signature():
    create = client.post(
        "/ideas",
        json={
            "title": "Invalid attachment idea",
            "description": "Idea with malicious attachment.",
            "tags": ["files"],
        },
    )
    assert create.status_code == 201
    idea = create.json()

    bad_data = b"not_an_image"
    resp = client.post(
        f"/ideas/{idea['id']}/attachments",
        files={"file": ("payload.png", bad_data, "application/octet-stream")},
    )
    expect_problem(resp, status=415, code="attachment_bad_type")


def test_rejects_missing_idea_without_writing_file():
    data = make_png(b"\x00" * 16)

    resp = client.post(
        "/ideas/999/attachments",
        files={"file": ("diagram.png", data, "image/png")},
    )
    expect_problem(resp, status=404, code="idea_not_found")
    assert list(attachment_storage.base_dir.iterdir()) == []


def test_cleanup_happens_when_storage_add_fails(monkeypatch):
    create = client.post(
        "/ideas",
        json={
            "title": "Cleanup idea",
            "description": "Need to ensure files are removed on failure.",
            "tags": ["files"],
        },
    )
    assert create.status_code == 201
    idea = create.json()

    def fail_add_attachment(*_args, **_kwargs):
        raise ApiProblem(code="storage_error", detail="cannot persist", status=503)

    monkeypatch.setattr(storage, "add_attachment", fail_add_attachment)

    data = make_png(b"\x00" * 32)
    resp = client.post(
        f"/ideas/{idea['id']}/attachments",
        files={"file": ("diagram.png", data, "image/png")},
    )
    expect_problem(resp, status=503, code="storage_error")
    assert list(attachment_storage.base_dir.iterdir()) == []
