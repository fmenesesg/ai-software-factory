"""Security stub agent tests."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_security_health() -> None:
    from agent_security.app import create_app

    client = TestClient(create_app())
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["agent"] == "security"
    assert body["mode"] == "stub"


def test_security_placeholder_check() -> None:
    from agent_security.app import create_app

    client = TestClient(create_app())
    body = client.post(
        "/v1/invoke",
        json={
            "run_id": "r1",
            "artifacts": {"pr_url": "https://github.com/o/r/pull/1"},
            "input": {"head_sha": "abc"},
        },
    ).json()
    assert body["status"] == "ok"
    assert body["artifacts"]["security_check"] == "asf/security-scan"
    assert "placeholder" in body["message"]
