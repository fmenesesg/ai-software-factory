"""Empty LangGraph SDLC skeleton — boots with memory or Postgres checkpointer."""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from agent_sdk.artifacts import ArtifactIds
from orchestrator.checkpoint import build_checkpointer, resolve_checkpoint_dsn
from orchestrator.events import StageEvent, StageEventType


class OrchestratorState(TypedDict, total=False):
    run_id: str
    stage: str
    artifacts: dict[str, Any]
    events: list[dict[str, Any]]


def _bootstrap_node(state: OrchestratorState) -> OrchestratorState:
    run_id = state.get("run_id") or "local-dev"
    event = StageEvent(
        type=StageEventType.STAGE_ENTERED,
        run_id=run_id,
        stage="bootstrap",
        payload={},
    )
    events = list(state.get("events") or [])
    events.append(event.model_dump())
    artifacts = state.get("artifacts") or ArtifactIds().model_dump()
    return {
        "run_id": run_id,
        "stage": "bootstrap",
        "artifacts": artifacts,
        "events": events,
    }


def build_empty_graph() -> StateGraph:
    """Build the M1 empty graph (bootstrap → END). Full slice nodes arrive M2+."""
    graph: StateGraph = StateGraph(OrchestratorState)
    graph.add_node("bootstrap", _bootstrap_node)
    graph.add_edge(START, "bootstrap")
    graph.add_edge("bootstrap", END)
    return graph


def create_compiled_graph(*, checkpoint_dsn: str | None = None) -> Any:
    """Compile empty graph with checkpointer from bootstrap DSN (or memory)."""
    dsn = resolve_checkpoint_dsn(checkpoint_dsn)
    checkpointer = build_checkpointer(dsn)
    return build_empty_graph().compile(checkpointer=checkpointer)
