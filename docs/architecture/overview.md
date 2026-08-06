# Architecture overview (C4 summary)

English C4-oriented summary of the AI Software Factory workshop MVP.  
Canonical Engram companions: design `sdd/ai-software-factory/design`, diagrams `sdd/ai-software-factory/design-diagrams`, ADR mirrors under [`adr/`](./adr/README.md).

## C4 L1 — System context

```mermaid
C4Context
title AI Software Factory — System Context
Person(presenter, "Presenter", "Drives workshop; audience observes")
System(factory, "AI Software Factory", "LangGraph SDLC + agents + MCP")
System_Ext(gh, "GitHub", "Issues, PRs, reviews, Checks — HITL bus")
System_Ext(ocp, "OpenShift + OSAI", "Cluster, Pipelines, GitOps, Granite")
System_Ext(ghcr, "ghcr.io", "MVP container registry")
System_Ext(rhdh, "RHDH", "Catalog/TechDocs visualization")
Rel(presenter, factory, "Bootstrap + start run")
Rel(factory, gh, "Artifacts + HITL gates")
Rel(factory, ocp, "Deploy agents, Tekton, ephemeral, Argo stub")
Rel(factory, ghcr, "Push/pull images")
Rel(presenter, rhdh, "Observe pipeline status")
Rel(rhdh, gh, "GitHub plugin data")
```

## Containers / components

```mermaid
flowchart TB
  subgraph Presenter
    BS[workshop-bootstrap]
  end
  subgraph Factory["ai-software-factory monorepo"]
    ORCH[orchestrator LangGraph]
    GW[inference-gateway]
    SDK[agent-sdk]
    AGENTS[agents: pm architect developer reviewer security qa documentation deployment sre]
    MCP[MCP: github fs git ocp k8s developer-hub]
    APP[sample-app orders/inventory]
  end
  OSAI[OSAI Granite]
  TEK[Tekton]
  ARGO[Argo stub]
  GH[(GitHub HITL)]
  GHCR[(ghcr.io)]
  RHDH[RHDH]
  OTEL[OTel collector]
  BS --> ORCH
  ORCH --> AGENTS
  AGENTS --> SDK
  SDK --> GW --> OSAI
  SDK --> MCP
  MCP --> GH
  TEK --> GHCR
  TEK --> APP
  ORCH --> ARGO
  ORCH & GW & MCP & TEK --> OTEL
  RHDH --> GH
```

## Happy path (sequence)

Issue → PM → Architect → **GitHub HITL** → Developer → PR → Reviewer → Tekton → ghcr.io → ephemeral URL → GitOps promote **HITL** → Argo stub → SRE notes.

## Live Granite vs emergency fallback

Default: agents → `packages/inference-gateway` → live OSAI/Granite.  
Emergency-only: `INFERENCE_FALLBACK=true` after retries; response + OTel `workshop.fallback` / `inference.fallback=true`. See [inference fallback](../workshop/inference-fallback.md).

## Ephemeral lifecycle

Tekton creates `NAMESPACE_PREFIX*` ns, deploys Helm sample-app, comments URL on PR; teardown via [`scripts/teardown-ephemeral.sh`](../../scripts/teardown-ephemeral.sh) and [teardown runbook](../workshop/teardown.md).

## Related diagrams

Full Mermaid set lives in Engram `sdd/ai-software-factory/design-diagrams` (C4, fallback sequence, ephemeral destroy).
