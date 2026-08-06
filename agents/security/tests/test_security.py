"""Security agent tests."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_security_health() -> None:
    from agent_security.app import create_app

    client = TestClient(create_app())
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["agent"] == "security"
    assert body["mode"] in {"stub", "deep"}


def test_security_placeholder_check() -> None:
    from agent_security.app import create_app

    client = TestClient(create_app())
    body = client.post(
        "/v1/invoke",
        json={
            "run_id": "r1",
            "artifacts": {"pr_url": "https://github.com/o/r/pull/1"},
            "input": {"head_sha": "abc", "profile": "standard"},
        },
    ).json()
    assert body["status"] == "ok"
    assert body["artifacts"]["security_check"] == "asf/security-scan"
    assert body["artifacts"]["deep_scan_enabled"] is False
    assert "skipped" in body["message"]


def test_security_deep_scan_full_profile() -> None:
    from agent_security.app import create_app

    client = TestClient(create_app())
    body = client.post(
        "/v1/invoke",
        json={
            "run_id": "r2",
            "artifacts": {"pr_url": "https://github.com/o/r/pull/2"},
            "input": {"head_sha": "def", "profile": "full"},
        },
    ).json()
    assert body["artifacts"]["deep_scan_enabled"] is True
    assert body["artifacts"]["deep_scan_check"] == "asf/deep-scan"
    assert "enabled" in body["message"]
