"""Developer Hub MCP tests (task 5.5)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from mcp_developer_hub.config import DeveloperHubMcpSettings
from mcp_developer_hub.server import create_app
from mcp_developer_hub.tools import DeveloperHubTools


def test_health() -> None:
    client = TestClient(create_app(DeveloperHubMcpSettings(dry_run=True)))
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["server"] == "mcp-developer-hub"
    assert body["hitl"] is False


def test_catalog_register_dry_run() -> None:
    settings = DeveloperHubMcpSettings(dry_run=True)
    tools = DeveloperHubTools(settings)
    result = tools.catalog_register({"entity_ref": "component:default/ai-software-factory"})
    assert result["dry_run"] is True
    assert result["registered"] is False


def test_catalog_register_and_query() -> None:
    settings = DeveloperHubMcpSettings(dry_run=False)
    tools = DeveloperHubTools(settings)
    reg = tools.catalog_register(
        {
            "entity_ref": "component:default/ai-software-factory",
            "metadata": {"title": "AI Software Factory"},
        }
    )
    assert reg["registered"] is True
    query = tools.catalog_query({"entity_ref": "component:default/ai-software-factory"})
    assert query["count"] == 1
    assert query["entities"][0]["entity_ref"] == "component:default/ai-software-factory"
