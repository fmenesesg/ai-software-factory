# Kind OSS demo path

Laptop-local AI Software Factory on **Kind + Podman**.

## Acceptance

1. `./scripts/kind-stack-up.sh` installs edge + Tekton + Argo CD + Jaeger + OTel + factory + issue poller.
2. Presenter creates a GitHub Issue on **`fmenesesg/asf-demo-app`** labeled **`asf/run`**.
3. Poller comments `asf-run-id: …` and starts `POST /v1/runs`.
4. Status board + Jaeger + `/orch/v1/runs` show stage progression.
5. Architect HITL: comment `asf-approve: <id>` on the Issue (or set `HITL_STATIC_APPROVAL_ID`).
6. After approval: agents continue through Tekton ephemeral; promote with Issue comment `asf-promote: <id>`.

## Stack

| Layer | Choice |
|-------|--------|
| Cluster | Kind `asf-kind` |
| Edge | Envoy Gateway + Kuadrant |
| Registry | `asf-registry/registry:5000` |
| CI | Tekton `sample-app-pr-kind` |
| GitOps | Argo CD + HITL-gated Application stub |
| Viz | Jaeger (`jaeger.asf.demo.local`) + OTel; Tekton Dashboard; Open WebUI; optional host [Laminar spike](laminar-spike.md) |
| Trigger | Issue poller (`label=asf/run`) |
| Code out | Developer agent → MCP fs/git/github → real PR on `asf-demo-app` (Quarkus Hello World template; `DRY_RUN=false`) |

## Prerequisites

```bash
kind kubectl helm cloud-provider-kind podman
sudo sysctl -w fs.inotify.max_user_instances=512
go install sigs.k8s.io/cloud-provider-kind@latest
```

## Bring up

```bash
export KIND_EXPERIMENTAL_PROVIDER=podman
export GITHUB_TOKEN=ghp_...
./scripts/kind-stack-up.sh
./scripts/kind-stack-smoke.sh
```

Patch the workshop Secret (see README), then create the labeled Issue.

### Tear down

```bash
./scripts/kind-stack-down.sh
./scripts/kind-stack-down.sh --cluster
```

### Rate-limit burst

```bash
for i in $(seq 1 12); do
  curl -sS -o /dev/null -w "%{http_code}\n" -H 'Host: asf.demo.local' http://127.0.0.1:8080/status/ || true
done
```

## Secrets

| Key | Required for |
|-----|----------------|
| `GITHUB_TOKEN` | Issue poller + MCP GitHub (live) |
| `GITHUB_OWNER` / `GITHUB_REPO` | Target repo |
| `OSAI_MODEL_ID` | Gateway model id (stub ok) |

Never commit `.env` or live tokens.

## Optional: host Ollama

```bash
ollama serve
# patch ConfigMap GATEWAY_STUB_MODE=false and OSAI_INFERENCE_URL=http://host.containers.internal:11434/v1
```

## Pins

See `platform/kind/VERSIONS.md`. Profile: `platform/profiles/kind-oss.yaml`.
