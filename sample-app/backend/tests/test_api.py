"""Backend unit tests (k8s-free)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sample_app_backend.db import init_schema, connect
from sample_app_backend.main import create_app


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("SAMPLE_APP_DB_PATH", str(db_path))
    conn = connect(db_path)
    init_schema(conn)
    conn.close()
    return TestClient(create_app(serve_frontend=False))


def test_health_ready(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["service"] == "sample-app"


def test_openapi_served(client: TestClient) -> None:
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert schema["info"]["title"] == "Sample Orders/Inventory API"
    assert "/api/v1/inventory" in schema["paths"]
    assert "/health" in schema["paths"]


def test_inventory_and_order_flow(client: TestClient) -> None:
    inv = client.get("/api/v1/inventory")
    assert inv.status_code == 200
    items = inv.json()["items"]
    assert any(i["sku"] == "SKU-WIDGET" for i in items)

    created = client.post("/api/v1/orders", json={"sku": "SKU-WIDGET", "quantity": 2})
    assert created.status_code == 201
    order = created.json()["order"]
    assert order["sku"] == "SKU-WIDGET"
    assert order["quantity"] == 2

    orders = client.get("/api/v1/orders")
    assert orders.status_code == 200
    assert any(o["id"] == order["id"] for o in orders.json()["orders"])


def test_unknown_sku_rejected(client: TestClient) -> None:
    resp = client.post("/api/v1/orders", json={"sku": "NOPE", "quantity": 1})
    assert resp.status_code == 400
