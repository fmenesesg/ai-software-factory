"""SRE agent — health/SLO notes from runtime artifacts."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from agent_sdk.otel import factory_span
from agent_sdk.runtime import AgentInvokeRequest, AgentInvokeResponse


def create_app() -> FastAPI:
    app = FastAPI(title="AI Software Factory SRE Agent", version="0.6.0")
    app.state.agent_name = "sre"

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"status": "ok", "agent": "sre", "mode": "active"}

    @app.post("/v1/invoke", response_model=AgentInvokeResponse)
    async def invoke(body: AgentInvokeRequest) -> AgentInvokeResponse:
        artifacts = dict(body.artifacts)
        ephemeral_url = artifacts.get("ephemeral_url") or body.input.get("ephemeral_url")
        ns_name = artifacts.get("ns_name") or body.input.get("ns_name")
        promote_approval = artifacts.get("promote_approval_id") or body.input.get(
            "promote_approval_id"
        )

        with factory_span(
            "agent.sre.invoke",
            run_id=body.run_id,
            agent="sre",
            stage="sre",
        ):
            slo_target = float(body.input.get("slo_availability") or 0.99)
            notes = body.input.get("summary") or (
                f"SRE notes run={body.run_id}: ns={ns_name or 'n/a'}, "
                f"ephemeral={ephemeral_url or 'n/a'}, "
                f"promote_approval={promote_approval or 'pending'}, "
                f"target_availability={slo_target:.3f}. "
                "Observe OTel workshop.run_id for token/cost and fallback flags."
            )
            artifacts["sre_health_notes"] = str(notes)[:2000]
            artifacts["slo_availability_target"] = slo_target
            if ephemeral_url:
                artifacts["ephemeral_url"] = ephemeral_url
            if ns_name:
                artifacts["ns_name"] = ns_name
            return AgentInvokeResponse(
                agent="sre",
                run_id=body.run_id,
                status="ok",
                artifacts=artifacts,
                message="sre health/SLO notes recorded",
            )

    return app


app = create_app()
