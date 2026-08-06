# GitOps promote (MVP)
#
# Desired state lives in-monorepo under `platform/gitops/desired/`.
# Promote flow:
# 1. Open a GitOps PR that pins the ghcr.io image digest.
# 2. Require GitHub review approval (HITL) — RHDH does not approve.
# 3. Record Argo Application stub sync evidence (`sync_evidence`) only when approved.
#
# Live Argo CD is optional for the workshop; the stub Application manifests the contract.
