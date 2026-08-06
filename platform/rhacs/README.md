# RHACS / TAS optional pack (PROFILE=full)

English docs. **ACM is out of scope** for this workshop.

## When enabled

- Bootstrap `PROFILE=full`
- ConfigMap `asf-rhacs-scan-policy` applied from this directory
- Deep scan Check `asf/deep-scan` published via `asf_pipelines.deep_scan`

## When disabled (default workshop)

`PROFILE=standard` keeps Security/QA placeholder Checks only (task 4.4).

## Quay

Optional image mirror is documented under `docs/workshop/registries.md`.
GHCR (`ghcr.io`) remains the MVP primary publish path.
