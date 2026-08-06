"""HTTP MCP bridge for git tools (/tools, /tools/call)."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from mcp_git.config import GitMcpSettings
from mcp_git.security import GitSecurityError
from mcp_git.tools import GitToolError, GitTools


class ToolCallRequest(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


def create_app(settings: GitMcpSettings | None = None, tools: GitTools | None = None) -> FastAPI:
    settings = settings or GitMcpSettings()
    tools = tools or GitTools(settings)
    app = FastAPI(title="MCP Git", version="0.2.0")
    app.state.settings = settings
    app.state.tools = tools

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "server": "mcp-git",
            "dry_run": settings.dry_run,
            "allowed_remote": settings.resolved_allowed_remote(),
        }

    @app.get("/tools")
    async def list_tools() -> dict[str, Any]:
        return {"tools": tools.list_tools()}

    @app.post("/tools/call")
    async def call_tool(body: ToolCallRequest) -> dict[str, Any]:
        try:
            return tools.call(body.name, body.arguments)
        except GitSecurityError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except GitToolError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return app


app = create_app()
