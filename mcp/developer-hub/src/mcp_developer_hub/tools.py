"""Developer Hub MCP tools — register/query catalog (visualization only)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from mcp_developer_hub.config import DeveloperHubMcpSettings


class DeveloperHubToolError(RuntimeError):
    pass


@dataclass
class DeveloperHubTools:
    settings: DeveloperHubMcpSettings
    _catalog: dict[str, dict[str, Any]] = field(default_factory=dict)

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "catalog_register",
                "description": "Register or upsert a catalog entity ref (RHDH viz; not HITL)",
            },
            {
                "name": "catalog_query",
                "description": "Query registered catalog entities by kind/name",
            },
        ]

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "catalog_register":
            return self.catalog_register(arguments)
        if name == "catalog_query":
            return self.catalog_query(arguments)
        raise DeveloperHubToolError(f"unknown tool: {name}")

    def catalog_register(self, arguments: dict[str, Any]) -> dict[str, Any]:
        entity_ref = str(arguments.get("entity_ref") or self.settings.catalog_entity)
        metadata = arguments.get("metadata") if isinstance(arguments.get("metadata"), dict) else {}
        if self.settings.dry_run:
            return {
                "ok": True,
                "dry_run": True,
                "entity_ref": entity_ref,
                "registered": False,
                "message": "dry-run: catalog register skipped",
            }
        self._catalog[entity_ref] = {
            "entity_ref": entity_ref,
            "metadata": metadata,
            "rhdh_url": self.settings.rhdh_url,
        }
        return {"ok": True, "dry_run": False, "entity_ref": entity_ref, "registered": True}

    def catalog_query(self, arguments: dict[str, Any]) -> dict[str, Any]:
        entity_ref = arguments.get("entity_ref")
        if entity_ref:
            hit = self._catalog.get(str(entity_ref))
            return {"ok": True, "entities": [hit] if hit else [], "count": 1 if hit else 0}
        # Seed default factory component when empty so query works in tests/demo.
        if not self._catalog:
            default = self.settings.catalog_entity
            self._catalog[default] = {
                "entity_ref": default,
                "metadata": {"title": "AI Software Factory"},
                "rhdh_url": self.settings.rhdh_url,
            }
        return {"ok": True, "entities": list(self._catalog.values()), "count": len(self._catalog)}
