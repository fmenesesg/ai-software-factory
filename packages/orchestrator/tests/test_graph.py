"""Orchestrator checkpoint + empty graph boot tests."""

from orchestrator.checkpoint import build_checkpointer, resolve_checkpoint_dsn
from orchestrator.graph import create_compiled_graph
from orchestrator.events import StageEventType


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


def test_empty_graph_boots_and_emits_stage_event() -> None:
    graph = create_compiled_graph(checkpoint_dsn=None)
    result = graph.invoke(
        {"run_id": "run-m1"},
        config={"configurable": {"thread_id": "run-m1"}},
    )
    assert result["stage"] == "bootstrap"
    assert result["events"]
    assert result["events"][0]["type"] == StageEventType.STAGE_ENTERED
    assert result["events"][0]["run_id"] == "run-m1"
