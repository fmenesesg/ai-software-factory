"""Security agent stub — contract-compliant no-op with placeholder Check result."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from agent_sdk.otel import factory_span
from agent_sdk.runtime import AgentInvokeRequest, AgentInvokeResponse
from asf_pipelines.scan_hooks import build_scan_check_stub


def create_app() -> FastAPI:
    app = FastAPI(title="AI Software Factory Security Agent (stub)", version="0.4.0")
    app.state.agent_name = "security"

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"status": "ok", "agent": "security", "mode": "stub"}

    @app.post("/v1/invoke", response_model=AgentInvokeResponse)
    async def invoke(body: AgentInvokeRequest) -> AgentInvokeResponse:
        artifacts = dict(body.artifacts)
        pr_url = artifacts.get("pr_url") or body.input.get("pr_url")
        with factory_span("agent.security.invoke", run_id=body.run_id, agent="security", stage="security"):
            head_sha = str(body.input.get("head_sha") or "0" * 40)
            check = build_scan_check_stub(
                check_name="asf/security-scan",
                title="Security scan placeholder",
                summary="MVP stub — deep scan deferred (task 4.5)",
                conclusion="neutral",
                head_sha=head_sha,
                details={"pr_url": pr_url or "", "stub": True},
            )
            artifacts["security_check"] = check["name"]
            return AgentInvokeResponse(
                agent="security",
                run_id=body.run_id,
                status="ok",
                artifacts=artifacts,
                message=f"placeholder scan check: {check['name']}",
            )

    return app


app = create_app()
