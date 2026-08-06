"""LangGraph SDLC graph — PM → Architect → HITL → Developer (M2 MVP slice)."""

from __future__ import annotations

import os
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from agent_sdk.artifacts import ArtifactIds
from orchestrator.checkpoint import build_checkpointer, resolve_checkpoint_dsn
from orchestrator.events import StageEvent, StageEventType
from orchestrator.hitl import GitHubReviewPoller, HitlPoller, StaticHitlPoller


class OrchestratorState(TypedDict, total=False):
    run_id: str
    stage: str
    artifacts: dict[str, Any]
    events: list[dict[str, Any]]
    hitl_reviews: list[dict[str, Any]]
    hitl_pull_number: int
    github_owner: str
    github_repo: str
    error: str


def _append_event(
    state: OrchestratorState,
    *,
    event_type: StageEventType,
    stage: str,
    payload: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    run_id = state.get("run_id") or "local-dev"
    event = StageEvent(
        type=event_type,
        run_id=run_id,
        stage=stage,
        payload=payload or {},
    )
    events = list(state.get("events") or [])
    events.append(event.model_dump())
    return events


def _bootstrap_node(state: OrchestratorState) -> OrchestratorState:
    artifacts = state.get("artifacts") or ArtifactIds().model_dump()
    events = _append_event(state, event_type=StageEventType.STAGE_ENTERED, stage="bootstrap")
    events = _append_event(
        {**state, "events": events},
        event_type=StageEventType.STAGE_COMPLETED,
        stage="bootstrap",
    )
    return {
        "run_id": state.get("run_id") or "local-dev",
        "stage": "bootstrap",
        "artifacts": artifacts,
        "events": events,
        "github_owner": state.get("github_owner")
        or os.environ.get("GITHUB_OWNER", "fmenesesg"),
        "github_repo": state.get("github_repo")
        or os.environ.get("GITHUB_REPO", "ai-software-factory"),
    }


def _pm_node(state: OrchestratorState) -> OrchestratorState:
    artifacts = dict(state.get("artifacts") or {})
    events = _append_event(state, event_type=StageEventType.STAGE_ENTERED, stage="pm")
    issue_url = artifacts.get("issue_url")
    if not issue_url:
        events = _append_event(
            {**state, "events": events},
            event_type=StageEventType.STAGE_COMPLETED,
            stage="pm",
            payload={"error": "missing issue_url"},
        )
        return {
            **state,
            "stage": "pm",
            "error": "missing issue_url",
            "events": events,
            "artifacts": artifacts,
        }
    if not artifacts.get("pm_notes_url"):
        artifacts["pm_notes_url"] = f"{issue_url}#pm-notes"
    events = _append_event(
        {**state, "events": events},
        event_type=StageEventType.STAGE_COMPLETED,
        stage="pm",
        payload={"pm_notes_url": artifacts["pm_notes_url"]},
    )
    return {**state, "stage": "pm", "artifacts": artifacts, "events": events, "error": ""}


def _architect_node(state: OrchestratorState) -> OrchestratorState:
    artifacts = dict(state.get("artifacts") or {})
    events = _append_event(state, event_type=StageEventType.STAGE_ENTERED, stage="architect")
    if not artifacts.get("pm_notes_url"):
        return {
            **state,
            "stage": "architect",
            "error": "missing pm_notes_url",
            "events": _append_event(
                {**state, "events": events},
                event_type=StageEventType.STAGE_COMPLETED,
                stage="architect",
                payload={"error": "missing pm_notes_url"},
            ),
            "artifacts": artifacts,
        }
    if not artifacts.get("design_path"):
        artifacts["design_path"] = f"docs/architecture/designs/{state.get('run_id', 'run')}.md"
    events = _append_event(
        {**state, "events": events},
        event_type=StageEventType.STAGE_COMPLETED,
        stage="architect",
        payload={"design_path": artifacts["design_path"]},
    )
    return {**state, "stage": "architect", "artifacts": artifacts, "events": events, "error": ""}


def _make_hitl_node(poller: HitlPoller):
    def _hitl_architect_node(state: OrchestratorState) -> OrchestratorState:
        artifacts = dict(state.get("artifacts") or {})
        events = _append_event(state, event_type=StageEventType.HITL_WAITING, stage="hitl_architect")
        existing = artifacts.get("architect_approval_id")
        if existing:
            events = _append_event(
                {**state, "events": events},
                event_type=StageEventType.STAGE_COMPLETED,
                stage="hitl_architect",
                payload={"architect_approval_id": existing},
            )
            return {
                **state,
                "stage": "hitl_architect",
                "artifacts": artifacts,
                "events": events,
                "error": "",
            }

        approval = poller.poll_architect_approval(
            owner=state.get("github_owner") or "fmenesesg",
            repo=state.get("github_repo") or "ai-software-factory",
            pull_number=state.get("hitl_pull_number"),
            reviews=list(state.get("hitl_reviews") or []),
        )
        if not approval:
            # Do not advance — stay waiting without inventing approval_id.
            return {
                **state,
                "stage": "hitl_waiting",
                "artifacts": artifacts,
                "events": events,
                "error": "architect_approval_required",
            }

        artifacts["architect_approval_id"] = approval
        events = _append_event(
            {**state, "events": events},
            event_type=StageEventType.STAGE_COMPLETED,
            stage="hitl_architect",
            payload={"architect_approval_id": approval},
        )
        return {
            **state,
            "stage": "hitl_architect",
            "artifacts": artifacts,
            "events": events,
            "error": "",
        }

    return _hitl_architect_node


def _developer_node(state: OrchestratorState) -> OrchestratorState:
    artifacts = dict(state.get("artifacts") or {})
    events = _append_event(state, event_type=StageEventType.STAGE_ENTERED, stage="developer")
    approval = artifacts.get("architect_approval_id")
    if not approval:
        events = _append_event(
            {**state, "events": events},
            event_type=StageEventType.STAGE_COMPLETED,
            stage="developer",
            payload={"blocked": True, "reason": "missing architect_approval_id"},
        )
        return {
            **state,
            "stage": "developer_blocked",
            "artifacts": artifacts,
            "events": events,
            "error": "developer_blocked_without_approval",
        }
    if not artifacts.get("pr_url"):
        owner = state.get("github_owner") or "fmenesesg"
        repo = state.get("github_repo") or "ai-software-factory"
        artifacts["pr_url"] = f"https://github.com/{owner}/{repo}/pull/{state.get('run_id', '0')}"
    events = _append_event(
        {**state, "events": events},
        event_type=StageEventType.STAGE_COMPLETED,
        stage="developer",
        payload={"pr_url": artifacts["pr_url"]},
    )
    return {
        **state,
        "stage": "developer",
        "artifacts": artifacts,
        "events": events,
        "error": "",
    }


def _route_after_hitl(state: OrchestratorState) -> str:
    if state.get("stage") == "hitl_waiting" or not (state.get("artifacts") or {}).get(
        "architect_approval_id"
    ):
        return "wait"
    return "developer"


def build_empty_graph() -> StateGraph:
    """Backward-compatible alias — M1 name retained; builds MVP slice graph."""
    return build_mvp_graph()


def build_mvp_graph(*, poller: HitlPoller | None = None) -> StateGraph:
    """PM → Architect → HITL (GitHub poll) → Developer."""
    hitl_poller: HitlPoller = poller or GitHubReviewPoller()
    graph: StateGraph = StateGraph(OrchestratorState)
    graph.add_node("bootstrap", _bootstrap_node)
    graph.add_node("pm", _pm_node)
    graph.add_node("architect", _architect_node)
    graph.add_node("hitl_architect", _make_hitl_node(hitl_poller))
    graph.add_node("developer", _developer_node)
    graph.add_edge(START, "bootstrap")
    graph.add_edge("bootstrap", "pm")
    graph.add_edge("pm", "architect")
    graph.add_edge("architect", "hitl_architect")
    graph.add_conditional_edges(
        "hitl_architect",
        _route_after_hitl,
        {"wait": END, "developer": "developer"},
    )
    graph.add_edge("developer", END)
    return graph


def create_compiled_graph(
    *,
    checkpoint_dsn: str | None = None,
    poller: HitlPoller | None = None,
) -> Any:
    """Compile MVP graph with checkpointer from bootstrap DSN (or memory)."""
    dsn = resolve_checkpoint_dsn(checkpoint_dsn)
    checkpointer = build_checkpointer(dsn)
    # Allow demo override via APPROVAL_ID for local dry runs without live GitHub.
    if poller is None:
        static_id = os.environ.get("HITL_STATIC_APPROVAL_ID")
        if static_id:
            poller = StaticHitlPoller(approval_id=static_id)
    return build_mvp_graph(poller=poller).compile(checkpointer=checkpointer)
