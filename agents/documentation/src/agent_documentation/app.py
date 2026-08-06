"""Documentation agent — produces TechDocs path + PR notes (ADR-006 contract)."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from agent_sdk.otel import factory_span
from agent_sdk.runtime import AgentInvokeRequest, AgentInvokeResponse


def create_app() -> FastAPI:
    app = FastAPI(title="AI Software Factory Documentation Agent", version="0.6.0")
    app.state.agent_name = "documentation"

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"status": "ok", "agent": "documentation", "mode": "active"}

    @app.post("/v1/invoke", response_model=AgentInvokeResponse)
    async def invoke(body: AgentInvokeRequest) -> AgentInvokeResponse:
        artifacts = dict(body.artifacts)
        issue_url = artifacts.get("issue_url") or body.input.get("issue_url")
        design_path = artifacts.get("design_path") or body.input.get("design_path")
        pr_url = artifacts.get("pr_url") or body.input.get("pr_url")

        with factory_span(
            "agent.documentation.invoke",
            run_id=body.run_id,
            agent="documentation",
            stage="documentation",
        ):
            if not issue_url and not pr_url:
                return AgentInvokeResponse(
                    agent="documentation",
                    run_id=body.run_id,
                    status="error",
                    artifacts=artifacts,
                    message="issue_url or pr_url required for documentation artifacts",
                )

            docs_path = (
                artifacts.get("techdocs_path")
                or body.input.get("techdocs_path")
                or "docs/workshop/run-notes.md"
            )
            notes = body.input.get("summary") or (
                f"TechDocs notes for run {body.run_id}: "
                f"issue={issue_url or 'n/a'}, design={design_path or 'n/a'}, "
                f"pr={pr_url or 'n/a'}. Audience observe-only."
            )
            artifacts["techdocs_path"] = docs_path
            artifacts["docs_pr_notes"] = str(notes)[:2000]
            return AgentInvokeResponse(
                agent="documentation",
                run_id=body.run_id,
                status="ok",
                artifacts=artifacts,
                message=f"documentation artifact: {docs_path}",
            )

    return app


app = create_app()
