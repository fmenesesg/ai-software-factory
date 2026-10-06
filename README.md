# AI Software Factory

Enterprise reference monorepo for a **presenter-led** AI software factory workshop.

One presenter drives the factory end to end. The audience observes — this is not a multi-team concurrent lab.

## Paths

| Path | Profile | Edge / inference |
|------|---------|------------------|
| **OpenShift workshop** | `standard` / `full` | OCP + OSAI/Granite (when cluster available) |
| **Kind OSS laptop** | `kind-oss` | Envoy Gateway + Kuadrant + host Ollama (small models) — **no paid RH products** |

Kind OSS reuses the KCD Argentina N-S pattern (`cloud-provider-kind` + EG + Kuadrant). See [docs/workshop/kind-oss.md](./docs/workshop/kind-oss.md) and [ADR-014](./docs/architecture/adr/014-kind-oss.md).

## Vision

A vertical slice of an agentic SDLC control plane:

1. Bootstrap workshop credentials and platform profile
2. Inference via an OpenAI-compatible gateway (live Granite on OCP, or small Ollama models on Kind)
3. PM → Architect → GitHub HITL → Developer → PR
4. Tekton build/test → registry → ephemeral namespace + URL on the PR
5. Reviewer + Security/QA (+ remaining agents on full / kind-oss)
6. GitOps promote HITL → Argo
7. Observe agent work (RHDH on OCP; **Langfuse** on Kind OSS)

## Workshop model

| Role | Expectation |
|------|-------------|
| Presenter | Runs bootstrap, orchestrator, and demo scripts |
| Audience | Observe-only |

Default OCP profile: `PROFILE=standard`. Laptop: `PROFILE=kind-oss`.

## Repository layout

| Path | Purpose |
|------|---------|
| `packages/` | Shared agent SDK, orchestrator, inference gateway |
| `agents/` | One Deployment per agent role |
| `mcp/` | MCP tool servers (GitHub, git, filesystem, OpenShift/K8s, …) |
| `platform/` | Profiles, Kind edge, Tekton, GitOps, observability |
| `sample-app/` | Extractable orders/inventory demo workload |
| `demo/workshop/` | Presenter scripts |
| `docs/` | English human docs and ADR mirrors |
| `scripts/` | Bootstrap, Kind up/down, workshop utilities |

## Kind OSS quick start

```bash
export KIND_EXPERIMENTAL_PROVIDER=podman
./scripts/kind-up.sh
# hosts: 127.0.0.1 asf.demo.local
# then Ollama on host + deploy apps with httproute.enabled=true
```

## Spec-driven design (Engram)

Authoritative SDD artifacts live in **Engram** under `sdd/ai-software-factory/*`.  
This repository has **no** `openspec/` tree (ADR-013).

## License

Apache License 2.0 — see [LICENSE](./LICENSE).

## Status

Milestones **M0–M8** delivered on `main`. **ADR-014 Kind OSS** edge scripts and profile added for laptop demos.

```bash
./scripts/workshop-bootstrap.sh --dry-run
python -m pytest -q
NAMESPACE_PREFIX=asf-workshop- DRY_RUN=true ./scripts/teardown-ephemeral.sh
```
