# Observability platform pack (M1)

Helm/values for the OpenTelemetry collector used by the workshop factory.

Canonical attribute schema (ADR-010):

| Attribute | Meaning |
|-----------|---------|
| `workshop.run_id` | Presenter run correlation id |
| `workshop.tokens.prompt` / `.completion` / `.total` | Inference token usage |
| `workshop.tool` | MCP tool name |
| `workshop.fallback` | Emergency inference fallback flag |
| `workshop.agent` / `workshop.stage` / `workshop.model_id` | Context |

See `otel-collector-values.yaml`. SDK helpers live in `packages/agent-sdk` (`agent_sdk.otel`, `agent_sdk.cost`).

## Cost dashboards (task 6.2)

- Sample Grafana dashboard: [`grafana/asf-cost-by-run.json`](./grafana/asf-cost-by-run.json)
- Offline HTML report from exported span attrs:

```bash
python platform/observability/cost_report.py spans.json -o /tmp/asf-cost.html
```

Cost is derived from `workshop.run_id` + token usage attributes (no secrets).
