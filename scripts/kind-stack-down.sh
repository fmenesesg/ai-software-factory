#!/usr/bin/env bash
# Tear down factory workloads + optional full Kind cluster.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CTX="kind-${ASF_KIND_CLUSTER:-asf-kind}"
FULL="${1:-}"

kubectl --context "${CTX}" delete ns asf-factory --ignore-not-found --wait=false 2>/dev/null || true

if [[ "${FULL}" == "--cluster" ]]; then
  "${ROOT}/scripts/kind-down.sh"
else
  printf 'kind-stack-down: removed ns asf-factory (edge Kind cluster kept). Use --cluster to delete asf-kind.\n'
fi
