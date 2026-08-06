"""Gateway health, stub, and live Granite proxy path tests."""

from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from inference_gateway.app import create_app
from inference_gateway.config import GatewaySettings


def test_health_ok() -> None:
    settings = GatewaySettings(stub_mode=True)
    app = create_app(settings)
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["stub_mode"] is True


def test_stub_chat_completions() -> None:
    settings = GatewaySettings(stub_mode=True)
    app = create_app(settings)
    client = TestClient(app)
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "ibm/granite-*-instruct",
            "messages": [{"role": "user", "content": "hello factory"}],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["object"] == "chat.completion"
    assert "hello factory" in body["choices"][0]["message"]["content"]
    assert body["usage"]["total_tokens"] > 0
    assert body["factory"]["stub"] is True


def test_live_path_uses_osai_model_id_and_returns_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    """Live path (stub_mode=false) proxies upstream and always returns usage tokens."""

    settings = GatewaySettings(
        stub_mode=False,
        upstream_url="https://osai.example/v1",
        upstream_model="ibm/granite-3.3-8b-instruct",
        upstream_api_key="test-key",
        max_retries=0,
        inference_fallback=False,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/chat/completions")
        import json

        payload = json.loads(request.content.decode())
        assert payload["model"] == "ibm/granite-3.3-8b-instruct"
        assert request.headers.get("Authorization") == "Bearer test-key"
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-live",
                "object": "chat.completion",
                "model": payload["model"],
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "granite says hi"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 11,
                    "completion_tokens": 7,
                    "total_tokens": 18,
                },
            },
        )

    transport = httpx.MockTransport(handler)

    real_async_client = httpx.AsyncClient

    def async_client_factory(*args, **kwargs):  # type: ignore[no-untyped-def]
        kwargs["transport"] = transport
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", async_client_factory)

    app = create_app(settings)
    client = TestClient(app)
    response = client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "ping"}]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["factory"]["stub"] is False
    assert body["factory"]["fallback"] is False
    assert body["model"] == "ibm/granite-3.3-8b-instruct"
    assert body["usage"]["prompt_tokens"] == 11
    assert body["usage"]["completion_tokens"] == 7
    assert body["usage"]["total_tokens"] == 18


def test_default_model_id_from_settings() -> None:
    settings = GatewaySettings(stub_mode=True, upstream_model="ibm/granite-*-instruct")
    assert settings.upstream_model == "ibm/granite-*-instruct"
