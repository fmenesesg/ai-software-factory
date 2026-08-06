"""PM agent FastAPI service — Issue → acceptance notes artifact handoff."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from agent_sdk.inference import InferenceClient, InferenceClientConfig
from agent_sdk.otel import factory_span
from agent_sdk.runtime import AgentInvokeRequest, AgentInvokeResponse, env_bool, env_gateway_url, env_model_id


def create_app() -> FastAPI:
    app = FastAPI(title="AI Software Factory PM Agent", version="0.2.0")
    app.state.agent_name = "pm"

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"status": "ok", "agent": "pm"}

    @app.post("/v1/invoke", response_model=AgentInvokeResponse)
    async def invoke(body: AgentInvokeRequest) -> AgentInvokeResponse:
        artifacts = dict(body.artifacts)
        issue_url = artifacts.get("issue_url") or body.input.get("issue_url")
        if not issue_url:
            return AgentInvokeResponse(
                agent="pm",
                run_id=body.run_id,
                status="error",
                artifacts=artifacts,
                message="issue_url is required",
            )

        with factory_span("agent.pm.invoke", run_id=body.run_id, agent="pm", stage="pm"):
            notes = body.input.get("acceptance_notes")
            usage: dict[str, int] | None = None
            if notes is None and not env_bool("AGENT_SKIP_INFERENCE", False):
                async with InferenceClient(
                    InferenceClientConfig(gateway_url=env_gateway_url(), model=env_model_id())
                ) as client:
                    completion = await client.chat_completions(
                        [
                            {
                                "role": "system",
                                "content": "You are the PM agent. Produce concise acceptance notes for the Issue.",
                            },
                            {
                                "role": "user",
                                "content": f"Issue: {issue_url}\nContext: {body.input}",
                            },
                        ]
                    )
                notes = completion["choices"][0]["message"]["content"]
                raw_usage = completion.get("usage") or {}
                usage = {
                    "prompt_tokens": int(raw_usage.get("prompt_tokens") or 0),
                    "completion_tokens": int(raw_usage.get("completion_tokens") or 0),
                    "total_tokens": int(raw_usage.get("total_tokens") or 0),
                }
            if notes is None:
                notes = f"PM acceptance notes for {issue_url}"

            # MVP stores notes URL as Issue comment URL placeholder when MCP not wired in-process.
            pm_notes_url = artifacts.get("pm_notes_url") or body.input.get("pm_notes_url")
            if not pm_notes_url:
                pm_notes_url = f"{issue_url}#pm-notes-{body.run_id}"
            artifacts["issue_url"] = issue_url
            artifacts["pm_notes_url"] = pm_notes_url
            return AgentInvokeResponse(
                agent="pm",
                run_id=body.run_id,
                status="ok",
                artifacts=artifacts,
                message=str(notes)[:2000],
                usage=usage,
            )

    return app


app = create_app()
