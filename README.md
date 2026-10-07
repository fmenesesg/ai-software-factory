# AI Software Factory

Presenter-led demo of an agentic SDLC control plane on a laptop Kind cluster.

**Acceptance:** create a GitHub Issue with label `asf/run` → the Kind stack starts the full factory run.

## What you get

| Piece | Role |
|-------|------|
| Envoy Gateway + Kuadrant | Edge (`asf.demo.local:8080`) + rate-limit (HTTP 429) |
| Inference gateway | OpenAI-compatible (stub by default) |
| Orchestrator | LangGraph: PM → Architect → HITL → Developer → Reviewer → Security → QA → Docs → Tekton → promote HITL → SRE |
| Agents + MCP | Deployed Services; orchestrator calls them over HTTP |
| Issue poller | Watches GitHub for `asf/run` and starts runs |
| Tekton | Kind ephemeral deploy of sample-app |
| Argo CD | Installed; promote sync still HITL-gated |
| Jaeger + OTel | Agent / run traces (`jaeger.asf.demo.local`) |
| Tekton Dashboard | PipelineRuns UI (`tekton.asf.demo.local`) |
| Open WebUI | Chat against inference gateway (`chat.asf.demo.local`) |
| Status board | Health of factory services |
| Sample app | Orders/inventory at `/` |

## Prerequisites

```bash
kind kubectl helm cloud-provider-kind podman
# optional on Linux:
sudo sysctl -w fs.inotify.max_user_instances=512
go install sigs.k8s.io/cloud-provider-kind@latest
```

## Run the demo

```bash
export KIND_EXPERIMENTAL_PROVIDER=podman
export GITHUB_TOKEN=ghp_...   # real token for Issue trigger
./scripts/kind-stack-up.sh    # first run builds images (several minutes)
./scripts/kind-stack-smoke.sh

# Install token into the cluster
kubectl --context kind-asf-kind -n asf-factory create secret generic asf-workshop-secrets \
  --from-literal=GITHUB_TOKEN="$GITHUB_TOKEN" \
  --from-literal=GITHUB_OWNER=fmenesesg \
  --from-literal=GITHUB_REPO=asf-demo-app \
  --from-literal=OSAI_MODEL_ID=stub-small-model \
  --dry-run=client -o yaml | kubectl --context kind-asf-kind apply -f -
kubectl --context kind-asf-kind -n asf-factory rollout restart \
  deploy/asf-issue-poller deploy/asf-orchestrator deploy/asf-mcp-github

echo '127.0.0.1 asf.demo.local jaeger.asf.demo.local tekton.asf.demo.local chat.asf.demo.local' | sudo tee -a /etc/hosts
```

Then create a GitHub Issue on [`fmenesesg/asf-demo-app`](https://github.com/fmenesesg/asf-demo-app) with label **`asf/run`**. Within ~30s the Issue gets an `asf-run-id` comment.

To pass Architect HITL from the Issue, comment: `asf-approve: demo-approval-1`

| URL | What |
|-----|------|
| http://asf.demo.local:8080/status/ | Health board |
| http://jaeger.asf.demo.local:8080/ | Jaeger UI (OTLP traces) |
| http://tekton.asf.demo.local:8080/ | Tekton Dashboard |
| http://chat.asf.demo.local:8080/ | Open WebUI → inference gateway |
| http://asf.demo.local:8080/orch/v1/runs | Orchestrator runs JSON |
| http://asf.demo.local:8080/ | Sample app |

Presenter talk track: [demo/workshop/presenter-script.md](./demo/workshop/presenter-script.md).  
More Kind detail: [docs/workshop/kind-oss.md](./docs/workshop/kind-oss.md).

### Tear down

```bash
./scripts/kind-stack-down.sh           # workloads only
./scripts/kind-stack-down.sh --cluster # also delete asf-kind
```

## Repo layout

| Path | Purpose |
|------|---------|
| `packages/` | Agent SDK, orchestrator, inference gateway |
| `agents/` | One Deployment per agent role |
| `mcp/` | MCP tool servers |
| `platform/kind/` | Kind edge, images, Jaeger, issue poller |
| `platform/pipelines/` | Tekton (incl. Kind ephemeral pipeline) |
| `sample-app/` | Demo workload |
| `scripts/` | `kind-stack-up` / `platform` / `smoke` / `down` |

## License

Apache License 2.0 — see [LICENSE](./LICENSE).
