"""HTTP MCP bridge for GitHub tools."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from mcp_github.config import GitHubMcpSettings
from mcp_github.security import GitHubSecurityError
from mcp_github.tools import GitHubToolError, GitHubTools


class ToolCallRequest(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


def create_app(
    settings: GitHubMcpSettings | None = None,
    tools: GitHubTools | None = None,
) -> FastAPI:
    settings = settings or GitHubMcpSettings()
    tools = tools or GitHubTools(settings)
    app = FastAPI(title="MCP GitHub", version="0.2.0")
    app.state.settings = settings
    app.state.tools = tools

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "server": "mcp-github",
            "dry_run": settings.dry_run,
            "owner": settings.github_owner,
            "repo": settings.github_repo,
            "token_configured": bool(settings.github_token),
        }

    @app.get("/tools")
    async def list_tools() -> dict[str, Any]:
        return {"tools": tools.list_tools()}

    @app.post("/tools/call")
    async def call_tool(body: ToolCallRequest) -> dict[str, Any]:
        try:
            return tools.call(body.name, body.arguments)
        except GitHubSecurityError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except GitHubToolError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return app


app = create_app()
