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

Milestone **M0** (repo bootstrap / layout). Implementation of agents, MCP servers, and sample-app code begins in later milestones.
