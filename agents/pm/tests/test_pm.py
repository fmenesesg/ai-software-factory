"""PM agent invoke tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _skip_inference(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_SKIP_INFERENCE", "true")


def test_pm_health_and_invoke() -> None:
    from agent_pm.app import create_app

    client = TestClient(create_app())
    assert client.get("/health").json()["agent"] == "pm"
    response = client.post(
        "/v1/invoke",
        json={
            "run_id": "r1",
            "artifacts": {"issue_url": "https://github.com/fmenesesg/asf-demo-app/issues/1"},
            "input": {"acceptance_notes": "Must ship HITL gate"},
        },
    )
    body = response.json()
    assert body["status"] == "ok"
    assert body["artifacts"]["pm_notes_url"]
