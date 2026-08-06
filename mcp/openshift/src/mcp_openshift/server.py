"""HTTP MCP bridge for OpenShift tools."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from mcp_openshift.config import OpenShiftMcpSettings
from mcp_openshift.security import OpenShiftSecurityError
from mcp_openshift.tools import OpenShiftToolError, OpenShiftTools


class ToolCallRequest(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


def create_app(
    settings: OpenShiftMcpSettings | None = None,
    tools: OpenShiftTools | None = None,
) -> FastAPI:
    settings = settings or OpenShiftMcpSettings()
    tools = tools or OpenShiftTools(settings)
    app = FastAPI(title="MCP OpenShift", version="0.3.0")
    app.state.settings = settings
    app.state.tools = tools

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "server": "mcp-openshift",
            "dry_run": settings.dry_run,
            "namespace_prefix": settings.namespace_prefix,
        }

    @app.get("/tools")
    async def list_tools() -> dict[str, Any]:
        return {"tools": tools.list_tools()}

    @app.post("/tools/call")
    async def call_tool(body: ToolCallRequest) -> dict[str, Any]:
        try:
            return tools.call(body.name, body.arguments)
        except OpenShiftSecurityError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except OpenShiftToolError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return app


app = create_app()
