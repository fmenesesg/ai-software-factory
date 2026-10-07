# Workshop bootstrap

English docs for presenter-led bootstrap of the AI Software Factory workshop session.

Audience observes; only the presenter runs this flow.

## Quick start

1. Copy `.env.example` → `.env` (never commit `.env`).
2. Fill MUST fields (see schema below).
3. Validate without writes:

```bash
./scripts/workshop-bootstrap.sh --dry-run
```

4. Persist a local session file under `.workshop/` (gitignored):

```bash
./scripts/workshop-bootstrap.sh
```

Missing MUST fields fail **before** any cluster mutate. `--dry-run` skips session writes and cluster applies.

## Parameter schema

| Field | Req | Notes |
|-------|-----|-------|
| `OCP_API_URL` | MUST | OpenShift API endpoint |
| `OCP_TOKEN` or `KUBECONFIG` | MUST | One of token or kubeconfig path |
| `OSAI_INFERENCE_URL` | MUST | Live Granite / OpenShift AI inference base URL |
| `OSAI_MODEL_ID` | MUST | Default docs placeholder: `ibm/granite-*-instruct` |
| `OSAI_API_KEY` | MAY | Only if the inference endpoint requires it |
| `GITHUB_TOKEN` | MUST | Scoped least-privilege (checklist below) |
| `GITHUB_OWNER` / `GITHUB_REPO` | MUST | Default `fmenesesg` / `asf-demo-app` (Issue trigger target) |
| `GHCR_TOKEN` | MUST | Write auth for `ghcr.io` image push |
| `RHDH_URL` / `RHDH_TOKEN` | SHOULD | Visualization only — not HITL authority |
| `GITOPS_REPO_URL` | SHOULD | Promote target (MVP may use monorepo `platform/gitops/`) |
| `NAMESPACE_PREFIX` | SHOULD | Isolate workshop namespaces (default `asf-workshop-`) |
| `PROFILE` | MUST | `minimal` \| `standard` \| `full` (workshop = `standard`) |
| `CHECKPOINT_DSN` | SHOULD | PostgreSQL DSN for LangGraph checkpoints (same host family as pgvector later) |
| `DRY_RUN` | MAY | Skip writes when `true` |
| `INFERENCE_FALLBACK` | MAY | Emergency recorded/local only — never primary narrative |

## RBAC / least-privilege token checklist

Prefer short-lived tokens. Revoke after the workshop (see teardown runbook in M8).

### OpenShift / Kubernetes

- Prefer a **namespaced** ServiceAccount bound under `NAMESPACE_PREFIX*`.
- Avoid cluster-admin for agent or presenter automation SAs.
- Typical needs for MVP demo (tighten further per cluster policy):
  - create/get/list/delete Namespace (or pre-create prefixed ns)
  - deploy Deployments, Services, Routes/Ingress in prefixed ns
  - get Pods/logs for demo debugging
- Do **not** grant agents unrestricted cluster-scoped mutate.

### GitHub (`GITHUB_TOKEN`)

Minimum scopes / fine-grained permissions for MVP:

| Area | Access |
|------|--------|
| Issues | Read/write (seed Issue, comments, acceptance notes) |
| Pull requests | Read/write (open PR, request reviews) |
| Contents | Read/write (commit via MCP git path; no force-push) |
| Checks | Read/write (pipeline / scan placeholders) |
| Metadata | Read |

Deny or avoid: admin org, delete repos, force-push to protected `main`, unrelated org repos.

Agent Deployment SAs and scoped token mounting are detailed in
[`agent-tokens.md`](./agent-tokens.md) (M2) — **no cluster-admin** on agent SAs.

### GHCR (`GHCR_TOKEN`)

- `write:packages` (or fine-grained package write) for `ghcr.io/<owner>/<image>`.
- Prefer a token scoped to the workshop package namespace.
- Pull-only tokens are insufficient for Tekton push.

### OpenShift AI / inference

- Use a token or key scoped to the serving runtime / model route only.
- Agents MUST call inference only via `packages/inference-gateway` — never embed OSAI URLs in agent Deployments.

### RHDH (optional)

- Read-oriented token for catalog / GitHub plugin visualization.
- RHDH is **not** HITL authority; GitHub remains the approval bus.

## Profiles

Resolved under `platform/profiles/`:

| Profile | Intent |
|---------|--------|
| `minimal` | Orchestrator + inference gateway + OTel; no full platform slice |
| `standard` | Workshop MVP vertical slice (agents, Tekton ephemeral, GitOps HITL stub, GHCR, RHDH viz, live Granite) |
| `full` | standard + later agents / RHACS / Quay options (not ACM) |

## Safety

- No secrets in git; `.workshop/` and `.env` are gitignored.
- Dry-run MUST skip cluster writes.
- Live Granite is the primary narrative; recorded/local fallback is emergency-only.
