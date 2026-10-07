"""Orchestrator FastAPI — full Kind OSS graph + HITL-aware runs."""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from orchestrator.checkpoint import resolve_checkpoint_dsn
from orchestrator.graph import create_compiled_graph
from orchestrator.hitl import StaticHitlPoller


class InvokeRequest(BaseModel):
    run_id: str = Field(default="local-dev")
    checkpoint_dsn: str | None = None
    artifacts: dict[str, Any] = Field(default_factory=dict)
    hitl_reviews: list[dict[str, Any]] = Field(default_factory=list)
    hitl_pull_number: int | None = None
    architect_approval_id: str | None = None
    promote_approval_id: str | None = None


# In-memory run index for HITL resume / status (demo-scale).
_RUNS: dict[str, dict[str, Any]] = {}


def create_app() -> FastAPI:
    app = FastAPI(title="AI Software Factory Orchestrator", version="0.7.0")
    dsn = resolve_checkpoint_dsn(os.environ.get("CHECKPOINT_DSN"))
    app.state.graph = create_compiled_graph(checkpoint_dsn=dsn)
    app.state.checkpoint_dsn = dsn
    app.state.runs = _RUNS

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "checkpoint": "postgres" if app.state.checkpoint_dsn else "memory",
            "graph": "kind-oss-full-sdlc",
            "agent_http": os.environ.get("ASF_AGENT_HTTP", "false"),
        }

    @app.get("/v1/runs")
    async def list_runs() -> dict[str, Any]:
        return {"runs": list(app.state.runs.values())}

    @app.get("/v1/runs/{run_id}")
    async def get_run(run_id: str) -> dict[str, Any]:
        return app.state.runs.get(run_id) or {"run_id": run_id, "error": "not_found"}

    @app.post("/v1/runs")
    async def start_run(body: InvokeRequest) -> dict[str, Any]:
        dsn = resolve_checkpoint_dsn(body.checkpoint_dsn)
        poller = None
        if body.architect_approval_id or body.promote_approval_id:
            poller = StaticHitlPoller(
                approval_id=body.architect_approval_id,
                promote_approval_id=body.promote_approval_id,
            )
        graph = create_compiled_graph(checkpoint_dsn=dsn, poller=poller)
        config = {"configurable": {"thread_id": body.run_id}}
        artifacts = dict(body.artifacts)
        if body.architect_approval_id:
            artifacts["architect_approval_id"] = body.architect_approval_id
        if body.promote_approval_id:
            artifacts["promote_approval_id"] = body.promote_approval_id
        payload: dict[str, Any] = {
            "run_id": body.run_id,
            "artifacts": artifacts,
            "hitl_reviews": body.hitl_reviews,
        }
        if body.hitl_pull_number is not None:
            payload["hitl_pull_number"] = body.hitl_pull_number
        result = graph.invoke(payload, config=config)
        out = {
            "run_id": body.run_id,
            "stage": result.get("stage"),
            "artifacts": result.get("artifacts", {}),
            "events": result.get("events", []),
            "error": result.get("error") or None,
            "checkpoint": "postgres" if dsn else "memory",
        }
        app.state.runs[body.run_id] = out
        return out

    return app


app = create_app()
