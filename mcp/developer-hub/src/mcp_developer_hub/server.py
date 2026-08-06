"""HTTP MCP bridge for Developer Hub / RHDH catalog tools."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from mcp_developer_hub.config import DeveloperHubMcpSettings
from mcp_developer_hub.tools import DeveloperHubToolError, DeveloperHubTools


class ToolCallRequest(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


def create_app(
    settings: DeveloperHubMcpSettings | None = None,
    tools: DeveloperHubTools | None = None,
) -> FastAPI:
    settings = settings or DeveloperHubMcpSettings()
    tools = tools or DeveloperHubTools(settings)
    app = FastAPI(title="MCP Developer Hub", version="0.6.0")
    app.state.settings = settings
    app.state.tools = tools

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "server": "mcp-developer-hub",
            "dry_run": settings.dry_run,
            "rhdh_url_configured": bool(settings.rhdh_url),
            "hitl": False,
        }

    @app.get("/tools")
    async def list_tools() -> dict[str, Any]:
        return {"tools": tools.list_tools()}

    @app.post("/tools/call")
    async def call_tool(body: ToolCallRequest) -> dict[str, Any]:
        try:
            return tools.call(body.name, body.arguments)
        except DeveloperHubToolError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return app


app = create_app()
