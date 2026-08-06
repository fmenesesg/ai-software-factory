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

See `otel-collector-values.yaml`. SDK helpers live in `packages/agent-sdk` (`agent_sdk.otel`).
