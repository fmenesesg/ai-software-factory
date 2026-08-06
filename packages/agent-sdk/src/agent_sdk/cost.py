"""Cost estimation helpers from OTel token attributes (ADR-010)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class TokenRateConfig:
    """USD per 1K tokens — workshop demo rates (override via env/config)."""

    prompt_per_1k: float = 0.0005
    completion_per_1k: float = 0.0015


def estimate_cost_usd(
    *,
    prompt_tokens: int,
    completion_tokens: int,
    rates: TokenRateConfig | None = None,
) -> float:
    """Estimate inference cost from token counts (non-secret OTel attrs)."""
    cfg = rates or TokenRateConfig()
    prompt = max(0, int(prompt_tokens))
    completion = max(0, int(completion_tokens))
    return (prompt / 1000.0) * cfg.prompt_per_1k + (completion / 1000.0) * cfg.completion_per_1k


def cost_by_run_id(
    spans: list[dict[str, Any]],
    *,
    rates: TokenRateConfig | None = None,
) -> dict[str, dict[str, float | int]]:
    """
    Aggregate token/cost by workshop.run_id from span attribute dicts.

    Expected keys per span: workshop.run_id, workshop.tokens.prompt,
    workshop.tokens.completion (or gen_ai.usage.* aliases).
    """
    cfg = rates or TokenRateConfig()
    by_run: dict[str, dict[str, float | int]] = {}
    for span in spans:
        attrs = span.get("attributes") if isinstance(span.get("attributes"), dict) else span
        if not isinstance(attrs, dict):
            continue
        run_id = attrs.get("workshop.run_id") or attrs.get("factory.run_id")
        if not run_id:
            continue
        prompt = int(
            attrs.get("workshop.tokens.prompt")
            or attrs.get("gen_ai.usage.input_tokens")
            or 0
        )
        completion = int(
            attrs.get("workshop.tokens.completion")
            or attrs.get("gen_ai.usage.output_tokens")
            or 0
        )
        bucket = by_run.setdefault(
            str(run_id),
            {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_usd": 0.0,
            },
        )
        bucket["prompt_tokens"] = int(bucket["prompt_tokens"]) + prompt
        bucket["completion_tokens"] = int(bucket["completion_tokens"]) + completion
        bucket["total_tokens"] = int(bucket["prompt_tokens"]) + int(bucket["completion_tokens"])
        bucket["cost_usd"] = float(bucket["cost_usd"]) + estimate_cost_usd(
            prompt_tokens=prompt,
            completion_tokens=completion,
            rates=cfg,
        )
    return by_run


def render_cost_html(by_run: dict[str, dict[str, float | int]], *, title: str = "ASF cost by run_id") -> str:
    """Simple enterprise-shaped HTML report (no secrets)."""
    rows = []
    for run_id, stats in sorted(by_run.items()):
        rows.append(
            "<tr>"
            f"<td>{run_id}</td>"
            f"<td>{stats['prompt_tokens']}</td>"
            f"<td>{stats['completion_tokens']}</td>"
            f"<td>{stats['total_tokens']}</td>"
            f"<td>{float(stats['cost_usd']):.6f}</td>"
            "</tr>"
        )
    body = "\n".join(rows) if rows else "<tr><td colspan='5'>No runs</td></tr>"
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"/><title>{title}</title>
<style>
body{{font-family:system-ui,sans-serif;margin:2rem}}
table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid #ccc;padding:.5rem;text-align:left}}
th{{background:#f4f4f4}}
</style></head>
<body>
<h1>{title}</h1>
<p>Derived from OTel attributes <code>workshop.run_id</code> and token usage (ADR-010).</p>
<table>
<thead><tr><th>run_id</th><th>prompt</th><th>completion</th><th>total</th><th>cost_usd</th></tr></thead>
<tbody>
{body}
</tbody>
</table>
</body></html>
"""
