#!/usr/bin/env bash
# Tear down Kind OSS edge for AI Software Factory (PROFILE=kind-oss).
# Deletes only cluster ASF_KIND_CLUSTER (default asf-kind). Never touches kind-cluster / kind-west.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=lib/cloud-provider-kind.sh
source "${ROOT}/scripts/lib/cloud-provider-kind.sh"

export KIND_EXPERIMENTAL_PROVIDER="${KIND_EXPERIMENTAL_PROVIDER:-podman}"
CLUSTER_NAME="${ASF_KIND_CLUSTER:-asf-kind}"

case "${CLUSTER_NAME}" in
  asf-kind) ;;
  *)
    printf 'error: refusing to delete non-allowlisted cluster %s (allowed: asf-kind)\n' "${CLUSTER_NAME}" >&2
    exit 1
    ;;
esac

if kind get clusters 2>/dev/null | grep -qx "${CLUSTER_NAME}"; then
  printf 'kind-down: deleting Kind cluster %s\n' "${CLUSTER_NAME}"
  kind delete cluster --name "${CLUSTER_NAME}"
else
  printf 'kind-down: cluster %s not present\n' "${CLUSTER_NAME}"
fi

asf_stop_cloud_provider_kind_if_ours
printf 'kind-down: done\n'
