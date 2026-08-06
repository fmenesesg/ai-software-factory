"""Cost aggregation tests (task 6.2)."""

from __future__ import annotations

from agent_sdk.cost import cost_by_run_id, estimate_cost_usd, render_cost_html


def test_estimate_cost_usd() -> None:
    cost = estimate_cost_usd(prompt_tokens=1000, completion_tokens=1000)
    assert abs(cost - 0.002) < 1e-9


def test_cost_by_run_id_aggregates() -> None:
    spans = [
        {
            "attributes": {
                "workshop.run_id": "run-a",
                "workshop.tokens.prompt": 100,
                "workshop.tokens.completion": 50,
            }
        },
        {
            "attributes": {
                "workshop.run_id": "run-a",
                "workshop.tokens.prompt": 100,
                "workshop.tokens.completion": 50,
            }
        },
        {
            "attributes": {
                "workshop.run_id": "run-b",
                "gen_ai.usage.input_tokens": 10,
                "gen_ai.usage.output_tokens": 5,
            }
        },
    ]
    by_run = cost_by_run_id(spans)
    assert by_run["run-a"]["prompt_tokens"] == 200
    assert by_run["run-a"]["completion_tokens"] == 100
    assert by_run["run-a"]["total_tokens"] == 300
    assert by_run["run-b"]["total_tokens"] == 15
    html = render_cost_html(by_run)
    assert "run-a" in html
    assert "cost_usd" in html
