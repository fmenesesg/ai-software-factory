#!/usr/bin/env bash
# Teardown ephemeral workshop namespaces matching NAMESPACE_PREFIX.
# Requires oc or kubectl. Never deletes namespaces outside the prefix.
set -euo pipefail

PREFIX="${NAMESPACE_PREFIX-asf-workshop-}"
DRY_RUN="${DRY_RUN:-false}"
KUBE_BIN="${KUBE_BIN:-}"

# Empty explicit PREFIX is refused (unset still defaults via ${VAR-default} above only when unset).
# ${VAR-default} does NOT substitute when VAR is set to empty — unlike ${VAR:-default}.
if [[ -z "${PREFIX}" ]]; then
  echo "NAMESPACE_PREFIX must be non-empty" >&2
  exit 1
fi

if [[ -z "${KUBE_BIN}" ]]; then
  if command -v oc >/dev/null 2>&1; then
    KUBE_BIN=oc
  elif command -v kubectl >/dev/null 2>&1; then
    KUBE_BIN=kubectl
  else
    echo "oc or kubectl is required" >&2
    exit 1
  fi
fi

echo "Using ${KUBE_BIN}; PREFIX=${PREFIX}; DRY_RUN=${DRY_RUN}"

mapfile -t NAMESPACES < <("${KUBE_BIN}" get ns -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' \
  | grep -E "^${PREFIX}" || true)

if [[ ${#NAMESPACES[@]} -eq 0 ]]; then
  echo "No namespaces matching prefix ${PREFIX}"
  exit 0
fi

for ns in "${NAMESPACES[@]}"; do
  case "${ns}" in
    "${PREFIX}"*) ;;
    *)
      echo "Refusing to delete namespace outside prefix: ${ns}" >&2
      exit 1
      ;;
  esac
  if [[ "${DRY_RUN}" == "true" ]]; then
    echo "DRY_RUN would delete namespace/${ns}"
  else
    echo "Deleting namespace/${ns}"
    "${KUBE_BIN}" delete namespace "${ns}" --wait=false
  fi
done
