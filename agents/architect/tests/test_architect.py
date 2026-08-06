"""Architect agent invoke tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _skip_inference(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_SKIP_INFERENCE", "true")


def test_architect_requires_pm_notes() -> None:
    from agent_architect.app import create_app

    client = TestClient(create_app())
    response = client.post(
        "/v1/invoke",
        json={"run_id": "r1", "artifacts": {"issue_url": "https://github.com/o/r/issues/1"}},
    )
    assert response.json()["status"] == "error"


def test_architect_emits_design_path() -> None:
    from agent_architect.app import create_app

    client = TestClient(create_app())
    response = client.post(
        "/v1/invoke",
        json={
            "run_id": "r1",
            "artifacts": {
                "issue_url": "https://github.com/o/r/issues/1",
                "pm_notes_url": "https://github.com/o/r/issues/1#note",
            },
            "input": {"design_summary": "ADR-M2"},
        },
    )
    body = response.json()
    assert body["status"] == "ok"
    assert body["artifacts"]["design_path"].startswith("docs/architecture/")
