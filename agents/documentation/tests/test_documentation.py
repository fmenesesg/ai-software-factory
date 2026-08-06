"""Documentation agent tests."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_documentation_health() -> None:
    from agent_documentation.app import create_app

    client = TestClient(create_app())
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["agent"] == "documentation"
    assert body["mode"] == "active"


def test_documentation_produces_artifacts() -> None:
    from agent_documentation.app import create_app

    client = TestClient(create_app())
    body = client.post(
        "/v1/invoke",
        json={
            "run_id": "r-docs",
            "artifacts": {
                "issue_url": "https://github.com/o/r/issues/1",
                "design_path": "docs/architecture/adr/001.md",
                "pr_url": "https://github.com/o/r/pull/2",
            },
            "input": {},
        },
    ).json()
    assert body["status"] == "ok"
    assert body["artifacts"]["techdocs_path"]
    assert "docs_pr_notes" in body["artifacts"]
    assert "documentation artifact" in body["message"]


def test_documentation_requires_issue_or_pr() -> None:
    from agent_documentation.app import create_app

    client = TestClient(create_app())
    body = client.post(
        "/v1/invoke",
        json={"run_id": "r-empty", "artifacts": {}, "input": {}},
    ).json()
    assert body["status"] == "error"
