"""MCP client skeleton — agents call tools only via MCP for covered operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass(slots=True)
class McpClientConfig:
    """Connection settings for an MCP server (SSE/HTTP bridge in M1)."""

    base_url: str
    timeout_seconds: float = 30.0
    dry_run: bool = False
    server_name: str = "mcp"


@dataclass
class McpToolCallResult:
    ok: bool
    name: str
    content: Any = None
    error: str | None = None
    dry_run: bool = False


@dataclass
class McpClient:
    """Minimal MCP tool client used by agents and the orchestrator.

    M1 provides list/call scaffolding with dry-run write blocking.
    Full protocol adapters land with mcp/* servers in M2+.
    """

    config: McpClientConfig
    _client: httpx.AsyncClient | None = field(default=None, init=False, repr=False)

    async def __aenter__(self) -> McpClient:
        self._client = httpx.AsyncClient(
            base_url=self.config.base_url.rstrip("/"),
            timeout=self.config.timeout_seconds,
        )
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("McpClient must be used as an async context manager")
        return self._client

    async def list_tools(self) -> list[dict[str, Any]]:
        client = self._ensure_client()
        response = await client.get("/tools")
        response.raise_for_status()
        payload = response.json()
        tools = payload.get("tools", payload)
        if not isinstance(tools, list):
            raise TypeError("MCP /tools must return a list or {tools: [...]}")
        return tools

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        *,
        mutating: bool = False,
    ) -> McpToolCallResult:
        if mutating and self.config.dry_run:
            return McpToolCallResult(
                ok=True,
                name=name,
                content={"blocked": True, "reason": "dry_run"},
                dry_run=True,
            )
        client = self._ensure_client()
        response = await client.post(
            "/tools/call",
            json={"name": name, "arguments": arguments or {}},
        )
        if response.status_code >= 400:
            return McpToolCallResult(
                ok=False,
                name=name,
                error=f"HTTP {response.status_code}: {response.text}",
            )
        return McpToolCallResult(ok=True, name=name, content=response.json())
