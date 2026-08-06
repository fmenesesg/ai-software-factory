"""QA stub agent tests."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_qa_health() -> None:
    from agent_qa.app import create_app

    client = TestClient(create_app())
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["agent"] == "qa"
    assert body["mode"] == "stub"


def test_qa_placeholder_check() -> None:
    from agent_qa.app import create_app

    client = TestClient(create_app())
    body = client.post(
        "/v1/invoke",
        json={
            "run_id": "r1",
            "artifacts": {
                "pr_url": "https://github.com/o/r/pull/1",
                "ephemeral_url": "https://sample.apps.example.com",
            },
        },
    ).json()
    assert body["status"] == "ok"
    assert body["artifacts"]["qa_check"] == "asf/qa-tests"
