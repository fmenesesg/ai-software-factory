# Agent tokens and ServiceAccounts (M2)

English guidance for presenter-led least-privilege credentials used by MVP agents
(`pm`, `architect`, `developer`) and MCP servers.

Audience observes; only the presenter provisions tokens.

## Principles

1. **No cluster-admin** on agent ServiceAccounts (`asf-agent-pm`, `asf-agent-architect`,
   `asf-agent-developer`). Agent Deployments under `agents/*/deploy/` bind a dedicated SA
   with no ClusterRole/cluster-admin binding.
2. **GitHub is HITL authority** — agents use a scoped `GITHUB_TOKEN` via MCP GitHub only.
3. **Inference via gateway only** — agents receive `INFERENCE_GATEWAY_URL`, never raw OSAI URLs.
4. Prefer short-lived tokens; revoke after the workshop.

## Agent ServiceAccounts

| Agent | SA name | Cluster privileges |
|-------|---------|--------------------|
| PM | `asf-agent-pm` | None (no RoleBinding to cluster-admin) |
| Architect | `asf-agent-architect` | None |
| Developer | `asf-agent-developer` | None |

OpenShift/Kubernetes mutations for ephemeral ns land later via `mcp/openshift` /
`mcp/kubernetes` with `NAMESPACE_PREFIX` scope (M3) — still not cluster-admin.

## Scoped `GITHUB_TOKEN` usage

Mount the token from `asf-workshop-secrets` (bootstrap-created). Agents and MCP servers
read `GITHUB_TOKEN` from the environment; never bake tokens into images or git.

| Consumer | Operations | Required access |
|----------|------------|-----------------|
| `mcp/github` | issues, PRs, reviews, comments | Issues R/W, Pull requests R/W, Metadata R |
| `mcp/git` | commit/push to session remote | Contents R/W (no force-push; wrong remote denied) |
| `agents/pm` | Issue notes via MCP | Issues R/W |
| `agents/architect` | design + review request via MCP | Contents R/W, Pull requests R/W |
| `agents/developer` | open PR after HITL approval | Pull requests R/W, Contents R/W |

Deny or avoid: org admin, delete repos, force-push to protected `main`, unrelated repos.

Threat-matrix RED tests under `mcp/git` and `mcp/github` assert:

- relative / `git -C` / wrong-remote rejection
- no shell `gh` concat; `--head` spoof and env injection denied
- empty commit success refused; `--force` push denied

## Dry-run

When `DRY_RUN=true`, MCP mutating tools return `{blocked: true, reason: dry_run}` and do
not write. Bootstrap `--dry-run` remains the pre-mutate gate for cluster session files.

## Related

- Bootstrap RBAC checklist: [`bootstrap.md`](./bootstrap.md)
- Parameter schema: [`.env.example`](../../.env.example)
