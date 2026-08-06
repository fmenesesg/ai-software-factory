"""Reviewer agent invoke tests — PR verdict on review_id."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _skip_inference(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_SKIP_INFERENCE", "true")


def test_reviewer_health() -> None:
    from agent_reviewer.app import create_app

    client = TestClient(create_app())
    assert client.get("/health").json() == {"status": "ok", "agent": "reviewer"}


def test_reviewer_requires_pr_url() -> None:
    from agent_reviewer.app import create_app

    client = TestClient(create_app())
    body = client.post("/v1/invoke", json={"run_id": "r1", "artifacts": {}}).json()
    assert body["status"] == "error"


def test_reviewer_approves_pr() -> None:
    from agent_reviewer.app import create_app

    client = TestClient(create_app())
    response = client.post(
        "/v1/invoke",
        json={
            "run_id": "r1",
            "artifacts": {"pr_url": "https://github.com/o/r/pull/9"},
            "input": {"verdict": "APPROVE", "comment": "LGTM light review"},
        },
    )
    body = response.json()
    assert body["status"] == "ok"
    assert body["artifacts"]["review_id"]
    assert body["artifacts"]["review_verdict"] == "APPROVE"
    assert "LGTM" in body["message"]


def test_reviewer_request_changes() -> None:
    from agent_reviewer.app import create_app

    client = TestClient(create_app())
    body = client.post(
        "/v1/invoke",
        json={
            "run_id": "r2",
            "artifacts": {"pr_url": "https://github.com/o/r/pull/10"},
            "input": {"verdict": "REQUEST_CHANGES", "review_id": "rev-42"},
        },
    ).json()
    assert body["artifacts"]["review_verdict"] == "REQUEST_CHANGES"
    assert body["artifacts"]["review_id"] == "rev-42"
