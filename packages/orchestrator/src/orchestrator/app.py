"""Orchestrator FastAPI skeleton — health + empty graph boot."""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from orchestrator.checkpoint import resolve_checkpoint_dsn
from orchestrator.graph import create_compiled_graph


class InvokeRequest(BaseModel):
    run_id: str = Field(default="local-dev")
    checkpoint_dsn: str | None = None


def create_app() -> FastAPI:
    app = FastAPI(title="AI Software Factory Orchestrator", version="0.1.0")
    dsn = resolve_checkpoint_dsn(os.environ.get("CHECKPOINT_DSN"))
    # Memory checkpointer for local boot when DSN unset; Postgres when provided.
    app.state.graph = create_compiled_graph(checkpoint_dsn=dsn)
    app.state.checkpoint_dsn = dsn

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "checkpoint": "postgres" if app.state.checkpoint_dsn else "memory",
            "graph": "empty-bootstrap",
        }

    @app.post("/v1/runs")
    async def start_run(body: InvokeRequest) -> dict[str, Any]:
        dsn = resolve_checkpoint_dsn(body.checkpoint_dsn)
        graph = create_compiled_graph(checkpoint_dsn=dsn)
        config = {"configurable": {"thread_id": body.run_id}}
        result = graph.invoke({"run_id": body.run_id}, config=config)
        return {
            "run_id": body.run_id,
            "stage": result.get("stage"),
            "events": result.get("events", []),
            "checkpoint": "postgres" if dsn else "memory",
        }

    return app


app = create_app()
