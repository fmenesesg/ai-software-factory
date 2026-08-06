"""Deployment agent tests."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_deployment_health() -> None:
    from agent_deployment.app import create_app

    client = TestClient(create_app())
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["agent"] == "deployment"


def test_deployment_pipeline_evidence() -> None:
    from agent_deployment.app import create_app

    client = TestClient(create_app())
    body = client.post(
        "/v1/invoke",
        json={
            "run_id": "r-dep",
            "artifacts": {
                "pr_url": "https://github.com/o/r/pull/3",
                "image_digest": "sha256:abc",
                "ephemeral_url": "https://sample.apps.example/",
                "ns_name": "asf-workshop-pr3",
            },
            "input": {},
        },
    ).json()
    assert body["status"] == "ok"
    assert body["artifacts"]["pipeline_run_url"]
    assert body["artifacts"]["image_digest"] == "sha256:abc"
    assert "deployment_evidence" in body["artifacts"]


def test_deployment_requires_pr() -> None:
    from agent_deployment.app import create_app

    client = TestClient(create_app())
    body = client.post(
        "/v1/invoke",
        json={"run_id": "r-empty", "artifacts": {}, "input": {}},
    ).json()
    assert body["status"] == "error"
