"""Reviewer agent FastAPI service — light PR verdict on GitHub."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import FastAPI

from agent_sdk.inference import InferenceClient, InferenceClientConfig
from agent_sdk.otel import factory_span
from agent_sdk.runtime import AgentInvokeRequest, AgentInvokeResponse, env_bool, env_gateway_url, env_model_id

_VALID_VERDICTS = frozenset({"APPROVE", "REQUEST_CHANGES", "COMMENT"})


def _normalize_verdict(raw: str | None) -> str:
    value = (raw or "APPROVE").strip().upper().replace("-", "_").replace(" ", "_")
    if value in {"APPROVED", "APPROVE"}:
        return "APPROVE"
    if value in {"REQUEST_CHANGES", "CHANGES_REQUESTED", "REQUESTCHANGES"}:
        return "REQUEST_CHANGES"
    if value in _VALID_VERDICTS:
        return value
    return "APPROVE"


def create_app() -> FastAPI:
    app = FastAPI(title="AI Software Factory Reviewer Agent", version="0.4.0")
    app.state.agent_name = "reviewer"

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"status": "ok", "agent": "reviewer"}

    @app.post("/v1/invoke", response_model=AgentInvokeResponse)
    async def invoke(body: AgentInvokeRequest) -> AgentInvokeResponse:
        artifacts = dict(body.artifacts)
        pr_url = artifacts.get("pr_url") or body.input.get("pr_url")
        if not pr_url:
            return AgentInvokeResponse(
                agent="reviewer",
                run_id=body.run_id,
                status="error",
                artifacts=artifacts,
                message="pr_url is required for Reviewer",
            )

        with factory_span("agent.reviewer.invoke", run_id=body.run_id, agent="reviewer", stage="reviewer"):
            verdict = _normalize_verdict(body.input.get("verdict"))
            comment = body.input.get("comment")
            usage = None
            if comment is None and not env_bool("AGENT_SKIP_INFERENCE", False):
                async with InferenceClient(
                    InferenceClientConfig(gateway_url=env_gateway_url(), model=env_model_id())
                ) as client:
                    completion = await client.chat_completions(
                        [
                            {
                                "role": "system",
                                "content": (
                                    "You are the light Reviewer agent. Reply with a short PR review comment. "
                                    "Prefer APPROVE unless a clear blocker is provided."
                                ),
                            },
                            {
                                "role": "user",
                                "content": f"PR: {pr_url}\nInput: {body.input}\nVerdict hint: {verdict}",
                            },
                        ]
                    )
                comment = completion["choices"][0]["message"]["content"]
                raw_usage = completion.get("usage") or {}
                usage = {
                    "prompt_tokens": int(raw_usage.get("prompt_tokens") or 0),
                    "completion_tokens": int(raw_usage.get("completion_tokens") or 0),
                    "total_tokens": int(raw_usage.get("total_tokens") or 0),
                }
            if comment is None:
                if verdict == "REQUEST_CHANGES":
                    comment = f"Requesting changes on {pr_url} (light review)."
                else:
                    comment = f"Approving {pr_url} (light review)."

            review_id = artifacts.get("review_id") or body.input.get("review_id") or f"review-{uuid4().hex[:12]}"
            artifacts["pr_url"] = pr_url
            artifacts["review_id"] = str(review_id)
            artifacts["review_verdict"] = verdict

            return AgentInvokeResponse(
                agent="reviewer",
                run_id=body.run_id,
                status="ok",
                artifacts=artifacts,
                message=str(comment)[:2000],
                usage=usage,
            )

    return app


app = create_app()
