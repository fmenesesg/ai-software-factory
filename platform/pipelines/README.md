# Tekton pipelines — sample-app PR → ghcr.io → ephemeral

MVP CI path (ADR-006 / ADR-012):

1. `sample-app-build-test-push` — unit test, build Containerfile, push to **ghcr.io**, emit `IMAGE_DIGEST`
2. `sample-app-deploy-ephemeral` — Helm install into `${NAMESPACE_PREFIX}pr-<N>`, emit URL + ns
3. `sample-app-pr-evidence` — PR comment + Check stub (`asf/ephemeral`) with URL + namespace

## Manifests

| Path | Kind |
|------|------|
| `tasks/*.yaml` | Tekton Tasks |
| `pipelines/sample-app-pr.yaml` | Pipeline |
| `pipelineruns/sample-app-pr-example.yaml` | Example PipelineRun (`DRY_RUN=true`) |
| `src/asf_pipelines/pr_evidence.py` | Comment/Check helper (unit-tested) |

## Success path evidence

On success the Pipeline results include:

- `IMAGE_DIGEST` — `sha256:<64 hex>` (artifact `image_digest`)
- `EPHEMERAL_URL` — Route/Service URL (artifact `ephemeral_url`)
- `NAMESPACE` — ephemeral ns (artifact `ns_name`)

Cluster-dependent ACs (live PipelineRun on OpenShift) are workshop-only. Local verification:

```bash
pytest platform/pipelines -q
# optional: kubectl apply --dry-run=client -f platform/pipelines/pipelines/
```

## Teardown

```bash
NAMESPACE_PREFIX=asf-workshop- DRY_RUN=true ./scripts/teardown-ephemeral.sh
```
