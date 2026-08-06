"""Developer agent FastAPI service — requires architect_approval_id; emits pr_url."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from agent_sdk.inference import InferenceClient, InferenceClientConfig
from agent_sdk.otel import factory_span
from agent_sdk.runtime import AgentInvokeRequest, AgentInvokeResponse, env_bool, env_gateway_url, env_model_id


def create_app() -> FastAPI:
    app = FastAPI(title="AI Software Factory Developer Agent", version="0.2.0")
    app.state.agent_name = "developer"

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"status": "ok", "agent": "developer"}

    @app.post("/v1/invoke", response_model=AgentInvokeResponse)
    async def invoke(body: AgentInvokeRequest) -> AgentInvokeResponse:
        artifacts = dict(body.artifacts)
        approval_id = artifacts.get("architect_approval_id")
        design_path = artifacts.get("design_path")
        issue_url = artifacts.get("issue_url")

        if not approval_id:
            return AgentInvokeResponse(
                agent="developer",
                run_id=body.run_id,
                status="blocked",
                artifacts=artifacts,
                message="Developer blocked: architect_approval_id required (GitHub HITL)",
            )
        if not design_path or not issue_url:
            return AgentInvokeResponse(
                agent="developer",
                run_id=body.run_id,
                status="error",
                artifacts=artifacts,
                message="design_path and issue_url are required",
            )

        with factory_span("agent.developer.invoke", run_id=body.run_id, agent="developer", stage="developer"):
            pr_url = artifacts.get("pr_url") or body.input.get("pr_url")
            message = body.input.get("summary")
            usage = None
            if message is None and not env_bool("AGENT_SKIP_INFERENCE", False):
                async with InferenceClient(
                    InferenceClientConfig(gateway_url=env_gateway_url(), model=env_model_id())
                ) as client:
                    completion = await client.chat_completions(
                        [
                            {
                                "role": "system",
                                "content": "You are the Developer agent. Summarize the PR to open.",
                            },
                            {
                                "role": "user",
                                "content": (
                                    f"Issue: {issue_url}\nDesign: {design_path}\n"
                                    f"Approval: {approval_id}"
                                ),
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
            if not pr_url:
                # Placeholder PR URL for offline/unit path; live path uses GitHub MCP.
                owner = body.input.get("owner") or "fmenesesg"
                repo = body.input.get("repo") or "ai-software-factory"
                pr_number = body.input.get("pr_number") or body.run_id
                pr_url = f"https://github.com/{owner}/{repo}/pull/{pr_number}"
            if message is None:
                message = f"PR {pr_url} from approved design {design_path}"

            artifacts["pr_url"] = pr_url
            return AgentInvokeResponse(
                agent="developer",
                run_id=body.run_id,
                status="ok",
                artifacts=artifacts,
                message=str(message)[:2000],
                usage=usage,
            )

    return app


app = create_app()
