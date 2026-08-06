"""Architect agent FastAPI service — design_path handoff + review request."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from agent_sdk.inference import InferenceClient, InferenceClientConfig
from agent_sdk.otel import factory_span
from agent_sdk.runtime import AgentInvokeRequest, AgentInvokeResponse, env_bool, env_gateway_url, env_model_id


def create_app() -> FastAPI:
    app = FastAPI(title="AI Software Factory Architect Agent", version="0.2.0")
    app.state.agent_name = "architect"

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"status": "ok", "agent": "architect"}

    @app.post("/v1/invoke", response_model=AgentInvokeResponse)
    async def invoke(body: AgentInvokeRequest) -> AgentInvokeResponse:
        artifacts = dict(body.artifacts)
        issue_url = artifacts.get("issue_url")
        pm_notes_url = artifacts.get("pm_notes_url")
        if not issue_url or not pm_notes_url:
            return AgentInvokeResponse(
                agent="architect",
                run_id=body.run_id,
                status="error",
                artifacts=artifacts,
                message="issue_url and pm_notes_url are required before Architect",
            )

        with factory_span("agent.architect.invoke", run_id=body.run_id, agent="architect", stage="architect"):
            design_path = artifacts.get("design_path") or body.input.get("design_path")
            if not design_path:
                design_path = f"docs/architecture/designs/{body.run_id}.md"

            message = body.input.get("design_summary")
            usage = None
            if message is None and not env_bool("AGENT_SKIP_INFERENCE", False):
                async with InferenceClient(
                    InferenceClientConfig(gateway_url=env_gateway_url(), model=env_model_id())
                ) as client:
                    completion = await client.chat_completions(
                        [
                            {
                                "role": "system",
                                "content": "You are the Architect agent. Draft a short design/ADR summary.",
                            },
                            {
                                "role": "user",
                                "content": f"Issue: {issue_url}\nPM notes: {pm_notes_url}",
                            },
                        ]
                    )
                message = completion["choices"][0]["message"]["content"]
                raw_usage = completion.get("usage") or {}
                usage = {
                    "prompt_tokens": int(raw_usage.get("prompt_tokens") or 0),
                    "completion_tokens": int(raw_usage.get("completion_tokens") or 0),
                    "total_tokens": int(raw_usage.get("total_tokens") or 0),
                }
            if message is None:
                message = f"Design at {design_path} for {issue_url} (review requested)"

            artifacts["design_path"] = design_path
            # Architect approval is filled by HITL poll — never invent approval_id here.
            return AgentInvokeResponse(
                agent="architect",
                run_id=body.run_id,
                status="ok",
                artifacts=artifacts,
                message=str(message)[:2000],
                usage=usage,
            )

    return app


app = create_app()
