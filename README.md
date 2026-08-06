# AI Software Factory

Enterprise reference monorepo for a **presenter-led** AI software factory workshop on OpenShift.

One presenter drives the factory end to end. The audience observes — this is not a multi-team concurrent lab.

## Vision

A vertical slice of an agentic SDLC control plane:

1. Bootstrap workshop credentials and platform profile
2. Live Granite inference via an OpenAI-compatible gateway
3. PM → Architect → GitHub HITL → Developer → PR
4. Tekton build/test → `ghcr.io` → ephemeral namespace + URL on the PR
5. Light Reviewer + Security/QA stubs
6. GitOps promote HITL → Argo stub sync
7. RHDH visualization of pipeline/check status (not HITL authority)

## Workshop model

| Role | Expectation |
|------|-------------|
| Presenter | Runs bootstrap, orchestrator, and demo scripts |
| Audience | Observe-only |

Profile for workshops: `PROFILE=standard` (see `.env.example`).

## Repository layout

| Path | Purpose |
|------|---------|
| `packages/` | Shared agent SDK, orchestrator, inference gateway |
| `agents/` | One Deployment per agent role |
| `mcp/` | MCP tool servers (GitHub, git, filesystem, OpenShift, …) |
| `platform/` | OpenShift AI, Tekton, GitOps, observability, profiles |
| `sample-app/` | Extractable orders/inventory demo workload |
| `demo/workshop/` | Presenter scripts (later milestones) |
| `docs/` | English human docs and ADR mirrors |
| `scripts/` | Bootstrap and workshop utilities |

## Spec-driven design (Engram)

Authoritative SDD artifacts (explore, proposal, spec, design, tasks, ADRs) live in **Engram** under topic keys `sdd/ai-software-factory/*`.

This repository intentionally has **no** `openspec/` tree (ADR-013). `docs/architecture/` holds human-readable mirrors and pointers only.

## License

Apache License 2.0 — see [LICENSE](./LICENSE).

## Status

Milestone **M4/M5 MVP** (light Reviewer, Security/QA stubs, docs-like path RED, scan Check hooks, GitOps promote HITL, Argo stub, RHDH viz).

```bash
# Schema validation without writes
./scripts/workshop-bootstrap.sh --dry-run

# Focused M4/M5 tests (k8s-free)
python -m pytest agents/reviewer agents/security agents/qa platform/gitops mcp/filesystem platform/pipelines/tests/test_scan_hooks.py -q

# Ephemeral teardown (prefix-scoped; dry-run)
NAMESPACE_PREFIX=asf-workshop- DRY_RUN=true ./scripts/teardown-ephemeral.sh
```

Cluster-dependent ACs (live PipelineRun / Route URL / Argo sync) require workshop OpenShift; manifests and unit tests cover the success-path contract without a cluster.
