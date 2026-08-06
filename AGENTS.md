# Agent guidance — AI Software Factory

Guidance for coding agents and human contributors working in this monorepo.

## Product context

- **Venue:** Presenter-led workshop (one presenter executes; audience observes).
- **License:** Apache-2.0.
- **Docs language:** English only.
- **SDD store:** Engram-only (`sdd/ai-software-factory/*`). Do **not** create `openspec/`.
- **Remote:** `https://github.com/fmenesesg/ai-software-factory.git`

## Architecture constraints (do not freelance)

1. **Monorepo** with extractable `sample-app/` (no hard imports from factory packages into sample-app).
2. **LangGraph** owns SDLC/HITL state; **Tekton** owns build/test/push/ephemeral deploy; **GitOps + GitHub** own promote HITL.
3. Agents call tools **only via MCP** for covered GitHub/FS/Git/OpenShift/K8s operations.
4. Agents call inference **only via** `packages/inference-gateway` (no direct OSAI URLs in agent config).
5. HITL authority is **GitHub only**; RHDH is visualization.
6. Live **Granite** is the primary narrative; recorded/local fallback is emergency-only.
7. Secrets are **bootstrap-prompted** — never hardcode cluster endpoints or tokens. Use `.env.example` as the parameter schema; never commit `.env`.

## Package boundaries

| Area | Own | Must not |
|------|-----|----------|
| `packages/agent-sdk` | Shared MCP/inference/OTel/contracts | Platform manifests |
| `packages/orchestrator` | LangGraph graph, HITL wait, artifact IDs | Direct cluster-admin |
| `packages/inference-gateway` | OpenAI-compatible proxy + fallback | Agent business logic |
| `agents/*` | One role per Deployment | Bypass MCP for covered tools |
| `mcp/*` | Scoped tool servers + audit spans | Shell-concat model-controlled commands |
| `platform/*` | Profiles, pipelines, GitOps, observability | Sample-app domain logic |
| `sample-app/*` | Orders/inventory workload | Depend on factory Python/Node packages |

## Milestone discipline

Implement only the assigned milestone / work unit. Do not implement M1+ during M0 bootstrap. Prefer chained PRs when review surface grows.

## Verification mindset

- Prefer dry-run / least-privilege tokens.
- Namespace work stays under `NAMESPACE_PREFIX`.
- Threat-matrix RED tests (git path, PR commands, commit/push, docs-like paths) apply when touching MCP/git surfaces.
