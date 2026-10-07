#!/usr/bin/env bash
# Smoke checks for Kind OSS full stack (edge + platform + factory).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CTX="kind-${ASF_KIND_CLUSTER:-asf-kind}"
HOST="${ASF_DEMO_HOST:-127.0.0.1}"
HDR=(-H "Host: asf.demo.local")

fail=0
check() {
  local name="$1" url="$2"
  shift 2
  local hdr=("${HDR[@]}")
  if [[ $# -gt 0 ]]; then
    hdr=("$@")
  fi
  code="$(curl -sS -o /tmp/asf-smoke.out -w '%{http_code}' --connect-timeout 3 "${hdr[@]}" "${url}" || echo 000)"
  if [[ "${code}" =~ ^2 ]]; then
    printf 'OK  %s (%s)\n' "${name}" "${code}"
  else
    printf 'FAIL %s (%s)\n' "${name}" "${code}"
    fail=1
  fi
}

printf 'context=%s\n' "${CTX}"
kubectl --context "${CTX}" -n asf-factory get deploy 2>/dev/null || true
echo

check "status-board" "http://${HOST}:8080/status/"
check "status-api" "http://${HOST}:8080/status/api/status"
check "sample-app" "http://${HOST}:8080/health"
check "inference-models" "http://${HOST}:8080/v1/models"
check "orchestrator-health" "http://${HOST}:8080/orch/health"

if kubectl --context "${CTX}" -n asf-observability get deploy/jaeger >/dev/null 2>&1; then
  # Jaeger 2 UI is at /; services list is /api/v3/services (legacy /api/services is 404).
  check "jaeger-ui" "http://${HOST}:8080/" -H "Host: jaeger.asf.demo.local"
  check "jaeger-services" "http://${HOST}:8080/api/v3/services" -H "Host: jaeger.asf.demo.local"
else
  printf 'SKIP jaeger (not installed)\n'
fi

if kubectl --context "${CTX}" -n tekton-pipelines get deploy/tekton-dashboard >/dev/null 2>&1; then
  check "tekton-dashboard" "http://${HOST}:8080/" -H "Host: tekton.asf.demo.local"
else
  printf 'SKIP tekton-dashboard (not installed)\n'
fi

if kubectl --context "${CTX}" -n asf-chat get deploy/open-webui >/dev/null 2>&1; then
  check "open-webui" "http://${HOST}:8080/" -H "Host: chat.asf.demo.local"
else
  printf 'SKIP open-webui (not installed)\n'
fi

if kubectl --context "${CTX}" -n tekton-pipelines get deploy >/dev/null 2>&1; then
  printf 'OK  tekton-namespace\n'
else
  printf 'FAIL tekton-namespace\n'
  fail=1
fi

if kubectl --context "${CTX}" -n argocd get deploy/argocd-server >/dev/null 2>&1; then
  printf 'OK  argocd-server\n'
else
  printf 'FAIL argocd-server\n'
  fail=1
fi

if kubectl --context "${CTX}" -n asf-factory get deploy/asf-issue-poller >/dev/null 2>&1; then
  printf 'OK  issue-poller-deploy\n'
else
  printf 'FAIL issue-poller-deploy\n'
  fail=1
fi

if [[ "${1:-}" == "--live-issue" ]]; then
  printf '\n--live-issue: create a GitHub Issue with label asf/run and watch:\n'
  printf '  kubectl -n asf-factory logs -f deploy/asf-issue-poller\n'
fi

exit "${fail}"
