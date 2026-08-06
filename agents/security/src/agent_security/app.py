"""Security agent — placeholder Checks; deep scan when PROFILE=full (tasks 4.5/7.1)."""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI

from agent_sdk.otel import factory_span
from agent_sdk.runtime import AgentInvokeRequest, AgentInvokeResponse
from asf_pipelines.deep_scan import build_deep_scan_check, plan_deep_scan
from asf_pipelines.scan_hooks import build_scan_check_stub


def create_app() -> FastAPI:
    app = FastAPI(title="AI Software Factory Security Agent", version="0.6.0")
    app.state.agent_name = "security"

    @app.get("/health")
    async def health() -> dict[str, Any]:
        plan = plan_deep_scan(profile=os.environ.get("PROFILE"))
        return {
            "status": "ok",
            "agent": "security",
            "mode": "deep" if plan.enabled else "stub",
            "profile": plan.profile,
        }

    @app.post("/v1/invoke", response_model=AgentInvokeResponse)
    async def invoke(body: AgentInvokeRequest) -> AgentInvokeResponse:
        artifacts = dict(body.artifacts)
        pr_url = artifacts.get("pr_url") or body.input.get("pr_url")
        profile = str(body.input.get("profile") or os.environ.get("PROFILE") or "standard")
        with factory_span("agent.security.invoke", run_id=body.run_id, agent="security", stage="security"):
            head_sha = str(body.input.get("head_sha") or "0" * 40)
            stub = build_scan_check_stub(
                check_name="asf/security-scan",
                title="Security scan placeholder",
                summary="MVP stub Check — deep scan gated by PROFILE=full",
                conclusion="neutral",
                head_sha=head_sha,
                details={"pr_url": pr_url or "", "stub": True},
            )
            artifacts["security_check"] = stub["name"]
            deep = build_deep_scan_check(
                profile=profile,
                head_sha=head_sha,
                image_digest=artifacts.get("image_digest") or body.input.get("image_digest"),
                pr_url=pr_url if isinstance(pr_url, str) else None,
            )
            artifacts["deep_scan_check"] = deep["name"]
            artifacts["deep_scan_enabled"] = plan_deep_scan(profile=profile).enabled
            return AgentInvokeResponse(
                agent="security",
                run_id=body.run_id,
                status="ok",
                artifacts=artifacts,
                message=(
                    f"security check: {stub['name']}; deep scan: "
                    f"{'enabled' if artifacts['deep_scan_enabled'] else 'skipped'} ({profile})"
                ),
            )

    return app


app = create_app()
