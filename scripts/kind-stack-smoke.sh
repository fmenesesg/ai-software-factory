#!/usr/bin/env bash
# Smoke checks for Kind OSS full stack.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CTX="kind-${ASF_KIND_CLUSTER:-asf-kind}"
HOST="${ASF_DEMO_HOST:-127.0.0.1}"
HDR=(-H "Host: asf.demo.local")

fail=0
check() {
  local name="$1" url="$2"
  code="$(curl -sS -o /tmp/asf-smoke.out -w '%{http_code}' --connect-timeout 3 "${HDR[@]}" "${url}" || echo 000)"
  if [[ "${code}" =~ ^2 ]]; then
    printf 'OK  %s (%s)\n' "${name}" "${code}"
  else
    printf 'FAIL %s (%s)\n' "${name}" "${code}"
    fail=1
  fi
}

printf 'context=%s\n' "${CTX}"
kubectl --context "${CTX}" -n asf-factory get deploy,pods 2>/dev/null || true
echo
check "status-board" "http://${HOST}:8080/status/"
check "status-api" "http://${HOST}:8080/status/api/status"
check "sample-app" "http://${HOST}:8080/health"
check "inference-models" "http://${HOST}:8080/v1/models"

# Rate-limit wow (may 429)
printf 'rate-limit burst:\n'
for i in $(seq 1 8); do
  c="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 2 "${HDR[@]}" "http://${HOST}:8080/status/" || echo 000)"
  printf ' %s' "${c}"
done
printf '\n'

exit "${fail}"
