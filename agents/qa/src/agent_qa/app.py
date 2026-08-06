"""QA agent stub — contract-compliant no-op with placeholder Check result."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from agent_sdk.otel import factory_span
from agent_sdk.runtime import AgentInvokeRequest, AgentInvokeResponse
from asf_pipelines.scan_hooks import build_scan_check_stub


def create_app() -> FastAPI:
    app = FastAPI(title="AI Software Factory QA Agent (stub)", version="0.4.0")
    app.state.agent_name = "qa"

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"status": "ok", "agent": "qa", "mode": "stub"}

    @app.post("/v1/invoke", response_model=AgentInvokeResponse)
    async def invoke(body: AgentInvokeRequest) -> AgentInvokeResponse:
        artifacts = dict(body.artifacts)
        pr_url = artifacts.get("pr_url") or body.input.get("pr_url")
        ephemeral_url = artifacts.get("ephemeral_url") or body.input.get("ephemeral_url")
        with factory_span("agent.qa.invoke", run_id=body.run_id, agent="qa", stage="qa"):
            head_sha = str(body.input.get("head_sha") or "0" * 40)
            check = build_scan_check_stub(
                check_name="asf/qa-tests",
                title="QA test placeholder",
                summary="MVP stub — full suites deferred (M6)",
                conclusion="neutral",
                head_sha=head_sha,
                details={
                    "pr_url": pr_url or "",
                    "ephemeral_url": ephemeral_url or "",
                    "stub": True,
                },
            )
            artifacts["qa_check"] = check["name"]
            return AgentInvokeResponse(
                agent="qa",
                run_id=body.run_id,
                status="ok",
                artifacts=artifacts,
                message=f"placeholder test check: {check['name']}",
            )

    return app


app = create_app()
