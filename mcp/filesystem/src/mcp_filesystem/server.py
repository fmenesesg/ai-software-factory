"""HTTP MCP bridge for filesystem tools."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from mcp_filesystem.config import FilesystemMcpSettings
from mcp_filesystem.tools import FilesystemSecurityError, FilesystemToolError, FilesystemTools


class ToolCallRequest(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


def create_app(
    settings: FilesystemMcpSettings | None = None,
    tools: FilesystemTools | None = None,
) -> FastAPI:
    settings = settings or FilesystemMcpSettings()
    tools = tools or FilesystemTools(settings)
    app = FastAPI(title="MCP Filesystem", version="0.2.0")
    app.state.settings = settings
    app.state.tools = tools

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "server": "mcp-filesystem",
            "dry_run": settings.dry_run,
            "workspace_root": str(tools.workspace_root),
        }

    @app.get("/tools")
    async def list_tools() -> dict[str, Any]:
        return {"tools": tools.list_tools()}

    @app.post("/tools/call")
    async def call_tool(body: ToolCallRequest) -> dict[str, Any]:
        try:
            return tools.call(body.name, body.arguments)
        except FilesystemSecurityError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except FilesystemToolError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return app


app = create_app()
