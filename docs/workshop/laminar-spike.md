# Laminar spike (Kind OSS agent UX)

Optional **host-side** [Laminar](https://github.com/lmnr-ai/lmnr) (Apache-2.0, pin **v0.2.5**) for agent/LLM-oriented traces. **Jaeger stays the Kind APM**; agents keep OTLP → in-cluster collector only (no agent SDK changes).

## Architecture

```
agents / MCP / orchestrator
        │ OTLP
        ▼
otel-collector (asf-observability)
   ├── otlp/jaeger → jaeger:4317
   └── otlphttp/laminar → host.containers.internal:8000
                              │ Bearer project API key
                              ▼
                     Laminar app-server (host compose :8000/:8001)
                     UI http://localhost:5667
```

## Bring up Laminar (host)

```bash
git clone --depth 1 --branch v0.2.5 https://github.com/lmnr-ai/lmnr.git .tmp/lmnr
cd .tmp/lmnr && cp .env.example .env   # or use existing .env
# Podman: fully-qualify short image names; SELinux :Z on ClickHouse bind mounts
# (see local docker-compose.yml patches if using Fedora/podman short-name-mode=enforcing)
podman compose up -d
# Wait until UI redirects to /sign-in and app-server /health is OK
curl -sf http://127.0.0.1:8000/health
```

Podman gotchas observed on Fedora:

| Issue | Fix |
|-------|-----|
| `short-name resolution enforced` | Prefix images with `docker.io/…` |
| `container_name: clickhouse` breaks deps | Remove `container_name` |
| ClickHouse `Permission denied` on bind config | Mount with `:Z,ro` |
| First boot stuck on ClickHouse migrations | Restart `lmnr_frontend_1` after CH is healthy |

## Project API key

```bash
# Local-email sign-in (self-hosted)
TOKEN=$(curl -sS -X POST http://127.0.0.1:5667/api/auth/sign-in/local-email \
  -H 'content-type: application/json' \
  -d '{"email":"asf-spike@example.com"}' | jq -r .token)

# Create workspace + project, then mint key
WS=$(curl -sS -X POST http://127.0.0.1:5667/api/workspaces \
  -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' \
  -d '{"name":"asf-spike"}' | jq -r .id)
PID=$(curl -sS -X POST "http://127.0.0.1:5667/api/workspaces/$WS/projects" \
  -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' \
  -d '{"name":"asf-kind-spike"}' | jq -r .id)
curl -sS -X POST http://127.0.0.1:5667/api/cli/api-key \
  -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' \
  -d "{\"projectId\":\"$PID\"}" | jq -r .apiKey
```

Store the key only in a cluster Secret (never commit):

```bash
kubectl --context kind-asf-kind -n asf-observability create secret generic otel-laminar-apikey \
  --from-literal=project-api-key="$LAMINAR_PROJECT_API_KEY"
kubectl --context kind-asf-kind apply -f platform/kind/otel/collector-laminar-dual-export.yaml
```

Base `collector.yaml` stays Jaeger-only so `kind-stack-up.sh` does not require Laminar.

## Kind → host networking

Kind node `/etc/hosts` maps `host.containers.internal` → `169.254.1.2`, but **pods do not**. The collector Deployment sets `hostAliases` to that IP (same pattern as host Ollama).

## Verify

```bash
# Spans from factory workloads should appear in Laminar ClickHouse
podman exec lmnr_clickhouse_1 clickhouse-client --user ch_user --password ch_passwd \
  -q "SELECT name, count() c FROM spans GROUP BY name ORDER BY c DESC LIMIT 20"

# UI
xdg-open http://localhost:5667/   # sign-in as asf-spike@example.com via local-email
```

Smoke: collector debug exporter still logs batches; Jaeger UI unchanged; Laminar shows `fastapi.*` / `GET /health` etc. from in-cluster services.

## Non-goals (this spike)

- No in-cluster Laminar Deployment
- No Langfuse / Phoenix
- No agent code or MCP changes
- Not a default dependency of `kind-stack-up.sh` (requires host compose + Secret)
