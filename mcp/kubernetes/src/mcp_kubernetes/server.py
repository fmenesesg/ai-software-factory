"""HTTP MCP bridge for Kubernetes tools."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from mcp_kubernetes.config import KubernetesMcpSettings
from mcp_kubernetes.security import KubernetesSecurityError
from mcp_kubernetes.tools import KubernetesToolError, KubernetesTools


class ToolCallRequest(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


def create_app(
    settings: KubernetesMcpSettings | None = None,
    tools: KubernetesTools | None = None,
) -> FastAPI:
    settings = settings or KubernetesMcpSettings()
    tools = tools or KubernetesTools(settings)
    app = FastAPI(title="MCP Kubernetes", version="0.3.0")
    app.state.settings = settings
    app.state.tools = tools

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "server": "mcp-kubernetes",
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
        except KubernetesSecurityError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except KubernetesToolError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return app


app = create_app()
