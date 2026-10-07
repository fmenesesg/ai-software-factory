# Presenter script — Kind OSS demo

**Venue:** one presenter executes; audience observes.  
**Acceptance:** open a GitHub Issue with label `asf/run` → factory run starts on Kind.

## Before the room

1. Tools on PATH: `kind kubectl helm cloud-provider-kind podman`
2. Export a GitHub token (Issues + PR read/write on the demo repo):

```bash
export GITHUB_TOKEN=ghp_...
export GITHUB_OWNER=fmenesesg
export GITHUB_REPO=asf-demo-app
```

3. Bring up the stack (first run builds images):

```bash
export KIND_EXPERIMENTAL_PROVIDER=podman
./scripts/kind-stack-up.sh
./scripts/kind-stack-smoke.sh
```

4. Install the live token into the cluster Secret:

```bash
kubectl --context kind-asf-kind -n asf-factory create secret generic asf-workshop-secrets \
  --from-literal=GITHUB_TOKEN="$GITHUB_TOKEN" \
  --from-literal=GITHUB_OWNER="${GITHUB_OWNER:-fmenesesg}" \
  --from-literal=GITHUB_REPO="${GITHUB_REPO:-asf-demo-app}" \
  --from-literal=OSAI_MODEL_ID=stub-small-model \
  --dry-run=client -o yaml | kubectl --context kind-asf-kind apply -f -
kubectl --context kind-asf-kind -n asf-factory rollout restart deploy/asf-issue-poller deploy/asf-orchestrator deploy/asf-mcp-github
```

5. Hosts (optional for browsers):

```bash
echo '127.0.0.1 asf.demo.local jaeger.asf.demo.local tekton.asf.demo.local chat.asf.demo.local' | sudo tee -a /etc/hosts
```

## Live talk track

| Step | Action | Audience sees |
|------|--------|---------------|
| 1 | Open status + Jaeger (+ optional Tekton / chat) | http://asf.demo.local:8080/status/ · http://jaeger.asf.demo.local:8080/ |
| 2 | Create GitHub Issue on **asf-demo-app** with label **`asf/run`** | Issue appears in the demo repo |
| 3 | Wait ≤30s | Issue comment `asf-run-id: …`; orchestrator stage advances |
| 4 | HITL pause | Stage `hitl_waiting` until approval |
| 5 | Approve Architect | Comment on the Issue: `asf-approve: demo-approval-1` (or set `HITL_STATIC_APPROVAL_ID`) |
| 6 | Resume | Developer → Reviewer → Security → QA → Docs → Tekton ephemeral → promote wait |
| 7 | Promote HITL | Comment `asf-promote: demo-promote-1` → SRE completes (GitOps gate) |
| 8 | Tear down | `./scripts/kind-stack-down.sh --cluster` |

## Watch execution

```bash
kubectl --context kind-asf-kind -n asf-factory logs -f deploy/asf-issue-poller
kubectl --context kind-asf-kind -n asf-factory logs -f deploy/asf-orchestrator
curl -sS -H 'Host: asf.demo.local' http://127.0.0.1:8080/orch/v1/runs | jq .
```

## Notes

- Inference defaults to **stub** (`GATEWAY_STUB_MODE=true`).
- Tekton Kind pipeline deploys the preloaded sample-app image into `asf-workshop-pr-<N>`.
- RHDH / RHACS / Quay are out of this Kind path (Jaeger + status board are the viz surface).
