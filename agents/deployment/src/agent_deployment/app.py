"""Deployment agent — pipeline trigger evidence (image digest + PipelineRun)."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from agent_sdk.otel import factory_span
from agent_sdk.runtime import AgentInvokeRequest, AgentInvokeResponse


def create_app() -> FastAPI:
    app = FastAPI(title="AI Software Factory Deployment Agent", version="0.6.0")
    app.state.agent_name = "deployment"

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"status": "ok", "agent": "deployment", "mode": "active"}

    @app.post("/v1/invoke", response_model=AgentInvokeResponse)
    async def invoke(body: AgentInvokeRequest) -> AgentInvokeResponse:
        artifacts = dict(body.artifacts)
        pr_url = artifacts.get("pr_url") or body.input.get("pr_url")
        image_digest = artifacts.get("image_digest") or body.input.get("image_digest")

        with factory_span(
            "agent.deployment.invoke",
            run_id=body.run_id,
            agent="deployment",
            stage="deployment",
        ):
            if not pr_url:
                return AgentInvokeResponse(
                    agent="deployment",
                    run_id=body.run_id,
                    status="error",
                    artifacts=artifacts,
                    message="pr_url required for deployment pipeline evidence",
                )

            pipeline_run = (
                artifacts.get("pipeline_run_url")
                or body.input.get("pipeline_run_url")
                or f"tekton://asf-workshop/pipelinerun/{body.run_id}"
            )
            digest = image_digest or body.input.get("image_digest_stub") or "sha256:pending"
            ephemeral_url = artifacts.get("ephemeral_url") or body.input.get("ephemeral_url")
            ns_name = artifacts.get("ns_name") or body.input.get("ns_name")

            artifacts["pipeline_run_url"] = pipeline_run
            artifacts["image_digest"] = digest
            if ephemeral_url:
                artifacts["ephemeral_url"] = ephemeral_url
            if ns_name:
                artifacts["ns_name"] = ns_name
            artifacts["deployment_evidence"] = (
                f"PipelineRun {pipeline_run} for {pr_url} digest={digest}"
            )
            return AgentInvokeResponse(
                agent="deployment",
                run_id=body.run_id,
                status="ok",
                artifacts=artifacts,
                message=f"deployment evidence: {pipeline_run}",
            )

    return app


app = create_app()
