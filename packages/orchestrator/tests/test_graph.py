"""Orchestrator checkpoint + MVP graph + HITL gate tests."""

from orchestrator.checkpoint import build_checkpointer, resolve_checkpoint_dsn
from orchestrator.events import StageEventType
from orchestrator.graph import create_compiled_graph
from orchestrator.hitl import GitHubReviewPoller, StaticHitlPoller


def test_resolve_checkpoint_dsn_from_environ() -> None:
    dsn = resolve_checkpoint_dsn(environ={"CHECKPOINT_DSN": "postgresql://u:p@localhost:5432/asf"})
    assert dsn == "postgresql://u:p@localhost:5432/asf"


def test_resolve_checkpoint_dsn_explicit_wins() -> None:
    dsn = resolve_checkpoint_dsn(
        "postgresql://explicit/db",
        environ={"CHECKPOINT_DSN": "postgresql://env/db"},
    )
    assert dsn == "postgresql://explicit/db"


def test_resolve_checkpoint_dsn_unset() -> None:
    assert resolve_checkpoint_dsn(environ={}) is None


def test_memory_checkpointer_when_unset() -> None:
    cp = build_checkpointer(None)
    assert cp.__class__.__name__ in {"MemorySaver", "InMemorySaver"}


def test_graph_boots_bootstrap_stage_event() -> None:
    graph = create_compiled_graph(
        checkpoint_dsn=None,
        poller=StaticHitlPoller(approval_id=None),
    )
    result = graph.invoke(
        {
            "run_id": "run-m2",
            "artifacts": {"issue_url": "https://github.com/fmenesesg/ai-software-factory/issues/1"},
        },
        config={"configurable": {"thread_id": "run-m2"}},
    )
    assert result["events"]
    assert result["events"][0]["type"] == StageEventType.STAGE_ENTERED
    assert result["events"][0]["run_id"] == "run-m2"


def test_hitl_blocks_developer_without_approval() -> None:
    graph = create_compiled_graph(
        checkpoint_dsn=None,
        poller=StaticHitlPoller(approval_id=None),
    )
    result = graph.invoke(
        {
            "run_id": "run-blocked",
            "artifacts": {"issue_url": "https://github.com/fmenesesg/ai-software-factory/issues/1"},
        },
        config={"configurable": {"thread_id": "run-blocked"}},
    )
    assert result["stage"] == "hitl_waiting"
    assert not (result.get("artifacts") or {}).get("architect_approval_id")
    assert result.get("error") == "architect_approval_required"
    assert "pr_url" not in (result.get("artifacts") or {}) or not result["artifacts"].get("pr_url")


def test_hitl_advances_with_approval_id() -> None:
    poller = GitHubReviewPoller()
    graph = create_compiled_graph(checkpoint_dsn=None, poller=poller)
    result = graph.invoke(
        {
            "run_id": "run-ok",
            "artifacts": {"issue_url": "https://github.com/fmenesesg/ai-software-factory/issues/1"},
            "hitl_reviews": [{"id": "review-99", "state": "APPROVED"}],
        },
        config={"configurable": {"thread_id": "run-ok"}},
    )
    assert result["stage"] == "developer"
    assert result["artifacts"]["architect_approval_id"] == "review-99"
    assert result["artifacts"]["design_path"]
    assert result["artifacts"]["pr_url"]
    assert poller.calls


def test_no_advance_without_inventing_approval() -> None:
    graph = create_compiled_graph(
        checkpoint_dsn=None,
        poller=GitHubReviewPoller(),
    )
    result = graph.invoke(
        {
            "run_id": "run-pending",
            "artifacts": {"issue_url": "https://github.com/fmenesesg/ai-software-factory/issues/2"},
            "hitl_reviews": [{"id": "r1", "state": "COMMENTED"}],
        },
        config={"configurable": {"thread_id": "run-pending"}},
    )
    assert result["stage"] == "hitl_waiting"
    assert result["artifacts"].get("architect_approval_id") is None
