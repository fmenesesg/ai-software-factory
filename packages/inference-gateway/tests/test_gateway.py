"""Gateway health and stub completion tests."""

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
