# Teardown runbook + secrets revoke checklist

Presenter-led cleanup after a workshop session. Audience observes.

## 1. Ephemeral namespaces

```bash
export NAMESPACE_PREFIX="${NAMESPACE_PREFIX:-asf-workshop-}"
DRY_RUN=true ./scripts/teardown-ephemeral.sh   # preview
DRY_RUN=false ./scripts/teardown-ephemeral.sh  # delete prefixed ns only
```

The script **refuses** empty prefixes and namespaces outside `NAMESPACE_PREFIX`.

## 2. Optional Argo / GitOps stubs

- Close or abandon open GitOps promote PRs that should not merge.
- Delete stub Applications only in the workshop namespace/prefix if applied.

## 3. Secrets revoke checklist

| Secret / token | Action |
|----------------|--------|
| `GITHUB_TOKEN` | Revoke or rotate fine-grained PAT / app install token |
| `GHCR_TOKEN` | Revoke package write credential |
| `OCP_TOKEN` / kubeconfig | Delete temporary SA token; rotate if shared |
| `OSAI_API_KEY` | Rotate if issued for the session |
| `RHDH_TOKEN` | Revoke visualization token (not HITL) |
| `QUAY_*` (optional) | Revoke if PROFILE=full Quay mirror was enabled |
| Session `.env` / `.workshop/` | Delete local session files; never commit |

## 4. Observability

- Confirm no secret values remain in OTel attributes (tokens are counts only).
- Archive `workshop.run_id` traces if needed for demos.

## 5. Verify

```bash
# No leftover prefixed namespaces
oc get ns | grep "${NAMESPACE_PREFIX}" || echo "clean"
```
