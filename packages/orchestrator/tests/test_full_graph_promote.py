"""Full graph reaches SRE when both HITL gates are satisfied."""

from orchestrator.graph import create_compiled_graph
from orchestrator.hitl import StaticHitlPoller


def test_full_graph_with_both_approvals() -> None:
    graph = create_compiled_graph(
        checkpoint_dsn=None,
        poller=StaticHitlPoller(approval_id="arch-1", promote_approval_id="promo-1"),
    )
    result = graph.invoke(
        {
            "run_id": "run-full",
            "artifacts": {
                "issue_url": "https://github.com/fmenesesg/asf-demo-app/issues/9",
                "architect_approval_id": "arch-1",
                "promote_approval_id": "promo-1",
            },
        },
        config={"configurable": {"thread_id": "run-full"}},
    )
    assert result["stage"] == "sre"
    assert result["artifacts"].get("sre_health_notes")
    assert result["artifacts"].get("pipeline_run_url")
    assert not result.get("error")
