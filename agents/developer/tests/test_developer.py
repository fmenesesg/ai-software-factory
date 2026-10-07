"""Developer agent invoke tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _skip_inference(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_SKIP_INFERENCE", "true")
    monkeypatch.setenv("AGENT_DEVELOPER_STUB_PR", "true")


def test_developer_blocked_without_approval() -> None:
    from agent_developer.app import create_app

    client = TestClient(create_app())
    response = client.post(
        "/v1/invoke",
        json={
            "run_id": "r1",
            "artifacts": {
                "issue_url": "https://github.com/o/r/issues/1",
                "design_path": "docs/architecture/designs/r1.md",
            },
        },
    )
    body = response.json()
    assert body["status"] == "blocked"


def test_developer_emits_pr_with_approval() -> None:
    from agent_developer.app import create_app

    client = TestClient(create_app())
    response = client.post(
        "/v1/invoke",
        json={
            "run_id": "r1",
            "artifacts": {
                "issue_url": "https://github.com/o/r/issues/1",
                "design_path": "docs/architecture/designs/r1.md",
                "architect_approval_id": "review-1",
            },
            "input": {"summary": "PR ready", "pr_url": "https://github.com/o/r/pull/9"},
        },
    )
    assert response.json()["artifacts"]["pr_url"].endswith("/pull/9")
