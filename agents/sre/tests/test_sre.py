"""SRE agent tests."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_sre_health() -> None:
    from agent_sre.app import create_app

    client = TestClient(create_app())
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["agent"] == "sre"


def test_sre_health_notes() -> None:
    from agent_sre.app import create_app

    client = TestClient(create_app())
    body = client.post(
        "/v1/invoke",
        json={
            "run_id": "r-sre",
            "artifacts": {
                "ephemeral_url": "https://sample.apps.example/",
                "ns_name": "asf-workshop-pr3",
                "promote_approval_id": "PRR_1",
            },
            "input": {"slo_availability": 0.995},
        },
    ).json()
    assert body["status"] == "ok"
    assert "sre_health_notes" in body["artifacts"]
    assert body["artifacts"]["slo_availability_target"] == 0.995
