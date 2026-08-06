# RHDH in the factory architecture

RHDH is the workshop **visualization** surface for the AI Software Factory.

| Concern | Owner |
|---------|--------|
| Architect / promote HITL | GitHub reviews & PR approvals |
| Pipeline / Check status display | RHDH + GitHub plugin |
| Catalog entity | `platform/rhdh/catalog-info.yaml` |

## Component

The `ai-software-factory` Component uses `github.com/project-slug` so the GitHub
plugin can render Checks for Tekton ephemeral evidence and Security/QA stubs.

## Out of scope (MVP)

- `mcp/developer-hub` registration tools (task 5.5, P1)
- Using RHDH as an approval UI
