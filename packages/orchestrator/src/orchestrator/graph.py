"""LangGraph SDLC graph — Issue → agents → HITL → PR → Tekton → promote gate."""

from __future__ import annotations

import os
import re
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from agent_sdk.artifacts import ArtifactIds
from orchestrator.agents_http import (
    agent_http_enabled,
    call_mcp_github,
    create_kind_pipelinerun,
    invoke_agent,
)
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


def _merge_agent(artifacts: dict[str, Any], resp: dict[str, Any]) -> dict[str, Any]:
    merged = dict(artifacts)
    merged.update(resp.get("artifacts") or {})
    return merged


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
        or os.environ.get("GITHUB_REPO", "asf-demo-app"),
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
    run_id = state.get("run_id") or "local-dev"
    if agent_http_enabled():
        try:
            resp = invoke_agent("pm", run_id=run_id, artifacts=artifacts)
            artifacts = _merge_agent(artifacts, resp)
            if resp.get("status") == "error":
                return {
                    **state,
                    "stage": "pm",
                    "error": resp.get("message") or "pm_error",
                    "events": events,
                    "artifacts": artifacts,
                }
        except Exception as exc:  # noqa: BLE001 — surface as stage error for demo
            return {
                **state,
                "stage": "pm",
                "error": f"pm_http:{exc}",
                "events": events,
                "artifacts": artifacts,
            }
    elif not artifacts.get("pm_notes_url"):
        artifacts["pm_notes_url"] = f"{issue_url}#pm-notes"
    events = _append_event(
        {**state, "events": events},
        event_type=StageEventType.STAGE_COMPLETED,
        stage="pm",
        payload={"pm_notes_url": artifacts.get("pm_notes_url")},
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
    run_id = state.get("run_id") or "local-dev"
    if agent_http_enabled():
        try:
            resp = invoke_agent("architect", run_id=run_id, artifacts=artifacts)
            artifacts = _merge_agent(artifacts, resp)
        except Exception as exc:  # noqa: BLE001
            return {
                **state,
                "stage": "architect",
                "error": f"architect_http:{exc}",
                "events": events,
                "artifacts": artifacts,
            }
    elif not artifacts.get("design_path"):
        artifacts["design_path"] = f"docs/architecture/designs/{run_id}.md"
    events = _append_event(
        {**state, "events": events},
        event_type=StageEventType.STAGE_COMPLETED,
        stage="architect",
        payload={"design_path": artifacts.get("design_path")},
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

        reviews = list(state.get("hitl_reviews") or [])
        pull_number = state.get("hitl_pull_number")
        # Live Kind: refresh reviews from MCP when pull exists.
        if agent_http_enabled() and pull_number and not reviews:
            try:
                listed = call_mcp_github(
                    "list_pull_reviews",
                    {
                        "owner": state.get("github_owner"),
                        "repo": state.get("github_repo"),
                        "pull_number": pull_number,
                    },
                )
                reviews = list(listed.get("reviews") or [])
            except Exception:
                reviews = []

        approval = poller.poll_architect_approval(
            owner=state.get("github_owner") or "fmenesesg",
            repo=state.get("github_repo") or "asf-demo-app",
            pull_number=pull_number,
            reviews=reviews,
        )
        if not approval:
            return {
                **state,
                "stage": "hitl_waiting",
                "artifacts": artifacts,
                "events": events,
                "error": "architect_approval_required",
                "hitl_reviews": reviews,
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
            "hitl_reviews": reviews,
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
    run_id = state.get("run_id") or "local-dev"
    owner = state.get("github_owner") or "fmenesesg"
    repo = state.get("github_repo") or "asf-demo-app"
    if agent_http_enabled():
        try:
            resp = invoke_agent(
                "developer",
                run_id=run_id,
                artifacts=artifacts,
                input_data={"owner": owner, "repo": repo},
            )
            artifacts = _merge_agent(artifacts, resp)
        except Exception as exc:  # noqa: BLE001
            return {
                **state,
                "stage": "developer",
                "error": f"developer_http:{exc}",
                "events": events,
                "artifacts": artifacts,
            }
    elif not artifacts.get("pr_url"):
        artifacts["pr_url"] = f"https://github.com/{owner}/{repo}/pull/{run_id}"
    events = _append_event(
        {**state, "events": events},
        event_type=StageEventType.STAGE_COMPLETED,
        stage="developer",
        payload={"pr_url": artifacts.get("pr_url")},
    )
    return {
        **state,
        "stage": "developer",
        "artifacts": artifacts,
        "events": events,
        "error": "",
    }


def _invoke_named_agent(stage: str, agent: str):
    def _node(state: OrchestratorState) -> OrchestratorState:
        artifacts = dict(state.get("artifacts") or {})
        events = _append_event(state, event_type=StageEventType.STAGE_ENTERED, stage=stage)
        run_id = state.get("run_id") or "local-dev"
        if agent_http_enabled():
            try:
                resp = invoke_agent(agent, run_id=run_id, artifacts=artifacts)
                artifacts = _merge_agent(artifacts, resp)
            except Exception as exc:  # noqa: BLE001
                return {
                    **state,
                    "stage": stage,
                    "error": f"{agent}_http:{exc}",
                    "events": events,
                    "artifacts": artifacts,
                }
        else:
            # Offline stubs keep artifact chain alive for unit tests / dry runs.
            if stage == "reviewer" and artifacts.get("pr_url"):
                artifacts.setdefault("review_verdict", "APPROVE")
                artifacts.setdefault("review_id", f"review-{run_id}")
            if stage == "security":
                artifacts.setdefault("security_check", "asf/security-scan")
            if stage == "qa":
                artifacts.setdefault("qa_check", "asf/qa-tests")
            if stage == "documentation":
                artifacts.setdefault("techdocs_path", "docs/workshop/run-notes.md")
            if stage == "sre":
                artifacts.setdefault("sre_health_notes", f"sre notes {run_id}")
        events = _append_event(
            {**state, "events": events},
            event_type=StageEventType.STAGE_COMPLETED,
            stage=stage,
        )
        return {**state, "stage": stage, "artifacts": artifacts, "events": events, "error": ""}

    return _node


def _deployment_node(state: OrchestratorState) -> OrchestratorState:
    artifacts = dict(state.get("artifacts") or {})
    events = _append_event(state, event_type=StageEventType.STAGE_ENTERED, stage="deployment")
    run_id = state.get("run_id") or "local-dev"
    pr_url = str(artifacts.get("pr_url") or "")
    pr_number = "0"
    m = re.search(r"/pull/(\d+)", pr_url)
    if m:
        pr_number = m.group(1)
    elif state.get("hitl_pull_number"):
        pr_number = str(state["hitl_pull_number"])

    if agent_http_enabled():
        try:
            resp = invoke_agent("deployment", run_id=run_id, artifacts=artifacts)
            artifacts = _merge_agent(artifacts, resp)
            tekton = create_kind_pipelinerun(run_id=run_id, pr_number=pr_number)
            artifacts["pipeline_run_url"] = tekton.get("pipeline_run_url") or artifacts.get(
                "pipeline_run_url"
            )
            artifacts.setdefault("image_digest", "sha256:kind-local")
            artifacts.setdefault(
                "ephemeral_url",
                f"http://sample-app.asf-workshop-pr-{pr_number}.svc.cluster.local:8080",
            )
            artifacts.setdefault("ns_name", f"asf-workshop-pr-{pr_number}")
        except Exception as exc:  # noqa: BLE001
            return {
                **state,
                "stage": "deployment",
                "error": f"deployment_http:{exc}",
                "events": events,
                "artifacts": artifacts,
            }
    else:
        artifacts.setdefault("pipeline_run_url", f"tekton://asf-factory/pipelinerun/{run_id}")
        artifacts.setdefault("image_digest", "sha256:pending")
        artifacts.setdefault("ephemeral_url", f"http://sample-app.asf-workshop-pr-{pr_number}.svc")
        artifacts.setdefault("ns_name", f"asf-workshop-pr-{pr_number}")

    events = _append_event(
        {**state, "events": events},
        event_type=StageEventType.STAGE_COMPLETED,
        stage="deployment",
        payload={
            "pipeline_run_url": artifacts.get("pipeline_run_url"),
            "ephemeral_url": artifacts.get("ephemeral_url"),
        },
    )
    return {**state, "stage": "deployment", "artifacts": artifacts, "events": events, "error": ""}


def _promote_hitl_node(state: OrchestratorState) -> OrchestratorState:
    """GitOps promote gate — requires promote_approval_id (never invent)."""
    artifacts = dict(state.get("artifacts") or {})
    events = _append_event(state, event_type=StageEventType.HITL_WAITING, stage="hitl_promote")
    if artifacts.get("promote_approval_id"):
        events = _append_event(
            {**state, "events": events},
            event_type=StageEventType.STAGE_COMPLETED,
            stage="hitl_promote",
            payload={"promote_approval_id": artifacts["promote_approval_id"]},
        )
        return {
            **state,
            "stage": "hitl_promote",
            "artifacts": artifacts,
            "events": events,
            "error": "",
        }
    return {
        **state,
        "stage": "promote_waiting",
        "artifacts": artifacts,
        "events": events,
        "error": "promote_approval_required",
    }


def _route_after_hitl(state: OrchestratorState) -> str:
    if state.get("stage") == "hitl_waiting" or not (state.get("artifacts") or {}).get(
        "architect_approval_id"
    ):
        return "wait"
    return "developer"


def _route_after_promote(state: OrchestratorState) -> str:
    if state.get("stage") == "promote_waiting" or not (state.get("artifacts") or {}).get(
        "promote_approval_id"
    ):
        return "wait"
    return "sre"


def build_empty_graph() -> StateGraph:
    """Backward-compatible alias — builds full Kind OSS graph."""
    return build_mvp_graph()


def build_mvp_graph(*, poller: HitlPoller | None = None) -> StateGraph:
    """Full demo graph: PM→Architect→HITL→Dev→Reviewer→Sec→QA→Docs→Deploy→promote HITL→SRE."""
    hitl_poller: HitlPoller = poller or GitHubReviewPoller()
    graph: StateGraph = StateGraph(OrchestratorState)
    graph.add_node("bootstrap", _bootstrap_node)
    graph.add_node("pm", _pm_node)
    graph.add_node("architect", _architect_node)
    graph.add_node("hitl_architect", _make_hitl_node(hitl_poller))
    graph.add_node("developer", _developer_node)
    graph.add_node("reviewer", _invoke_named_agent("reviewer", "reviewer"))
    graph.add_node("security", _invoke_named_agent("security", "security"))
    graph.add_node("qa", _invoke_named_agent("qa", "qa"))
    graph.add_node("documentation", _invoke_named_agent("documentation", "documentation"))
    graph.add_node("deployment", _deployment_node)
    graph.add_node("hitl_promote", _promote_hitl_node)
    graph.add_node("sre", _invoke_named_agent("sre", "sre"))

    graph.add_edge(START, "bootstrap")
    graph.add_edge("bootstrap", "pm")
    graph.add_edge("pm", "architect")
    graph.add_edge("architect", "hitl_architect")
    graph.add_conditional_edges(
        "hitl_architect",
        _route_after_hitl,
        {"wait": END, "developer": "developer"},
    )
    graph.add_edge("developer", "reviewer")
    graph.add_edge("reviewer", "security")
    graph.add_edge("security", "qa")
    graph.add_edge("qa", "documentation")
    graph.add_edge("documentation", "deployment")
    graph.add_edge("deployment", "hitl_promote")
    graph.add_conditional_edges(
        "hitl_promote",
        _route_after_promote,
        {"wait": END, "sre": "sre"},
    )
    graph.add_edge("sre", END)
    return graph


def create_compiled_graph(
    *,
    checkpoint_dsn: str | None = None,
    poller: HitlPoller | None = None,
) -> Any:
    """Compile graph with checkpointer from bootstrap DSN (or memory)."""
    dsn = resolve_checkpoint_dsn(checkpoint_dsn)
    checkpointer = build_checkpointer(dsn)
    if poller is None:
        static_id = os.environ.get("HITL_STATIC_APPROVAL_ID")
        promote_id = os.environ.get("HITL_STATIC_PROMOTE_APPROVAL_ID")
        if static_id:
            poller = StaticHitlPoller(
                approval_id=static_id,
                promote_approval_id=promote_id,
            )
    return build_mvp_graph(poller=poller).compile(checkpointer=checkpointer)
