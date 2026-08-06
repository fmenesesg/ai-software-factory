# Sample application — orders/inventory

Neutral cloud-native demo workload for the AI Software Factory workshop (ADR-012).
Extractable from the monorepo later (ADR-001). **Do not** import factory packages
(`packages/*`, `mcp/*`, `agents/*`) into this tree.

## Layout

| Path | Role |
|------|------|
| `backend/` | FastAPI REST + OpenAPI + `/health` |
| `frontend/` | Static HTML/JS served by the backend |
| `db/` | SQLite schema (Postgres optional; see `db/README.md`) |
| `helm/` | Chart with liveness/readiness probes + OpenShift Route |
| `Containerfile` | Image for `ghcr.io` (MVP registry) |

## Local run (k8s-free)

```bash
cd sample-app/backend
PYTHONPATH=src python -m uvicorn sample_app_backend.main:app --reload --port 8080
# GET http://127.0.0.1:8080/health
# OpenAPI: http://127.0.0.1:8080/docs
```

```bash
pytest sample-app/backend -q
helm lint sample-app/helm
```

## Cluster install (when available)

```bash
helm upgrade --install sample-app ./sample-app/helm \
  --namespace "${NAMESPACE_PREFIX}pr-123" \
  --create-namespace \
  --set image.digest=sha256:...
```

Health ready AC: Deployment readiness probe hits `/ready`; `/health` returns `status: ready`.
Cluster-dependent ACs (live Route URL) are validated in workshop runs; local validation uses
`helm lint` + chart template + backend pytest.
