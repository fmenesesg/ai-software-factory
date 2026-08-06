# Container registries

## MVP primary: GHCR

CI publishes sample-app images to **`ghcr.io`** (see Tekton `sample-app-build-test-push`).

Example:

```text
ghcr.io/fmenesesg/ai-software-factory-sample-app@sha256:…
```

## Optional: Quay (PROFILE=full)

Quay is an **optional mirror**, not the MVP primary.

Enable only when:

- `PROFILE=full`
- Quay org configured (`QUAY_ORG`)
- Presenter explicitly wants a secondary push

Python helper: `asf_pipelines.registry.plan_registry_publish(..., enable_quay=True, profile="full")`.

ConfigMap notes: `platform/rhacs/scan-policy.yaml` (`asf-registry-publish`).
