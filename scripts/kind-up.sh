#!/usr/bin/env bash
# Bring up Kind OSS edge for AI Software Factory (PROFILE=kind-oss).
# Pattern: KCD Argentina N-S — Envoy Gateway + Kuadrant + cloud-provider-kind.
# Does NOT install Contour, MetalLB, Linkerd, Skupper, or paid RH products.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=lib/cloud-provider-kind.sh
source "${ROOT}/scripts/lib/cloud-provider-kind.sh"

export KIND_EXPERIMENTAL_PROVIDER="${KIND_EXPERIMENTAL_PROVIDER:-podman}"
CLUSTER_NAME="${ASF_KIND_CLUSTER:-asf-kind}"
CTX="kind-${CLUSTER_NAME}"
KIND_DIR="${ROOT}/platform/kind"
GATEWAY_DIR="${KIND_DIR}/gateway"
KUADRANT_DIR="${KIND_DIR}/kuadrant"

EG_CHART_VERSION="${EG_CHART_VERSION:-v1.7.0}"
KUADRANT_CHART_VERSION="${KUADRANT_CHART_VERSION:-1.5.2}"

die() { printf 'error: %s\n' "$*" >&2; exit 1; }

prereq() {
  command -v kind >/dev/null || die "kind not on PATH"
  command -v kubectl >/dev/null || die "kubectl not on PATH"
  command -v helm >/dev/null || die "helm not on PATH"
  command -v cloud-provider-kind >/dev/null || die "cloud-provider-kind not on PATH (go install sigs.k8s.io/cloud-provider-kind@latest)"
  if [[ "$(sysctl -n fs.inotify.max_user_instances 2>/dev/null || echo 0)" -lt 512 ]]; then
    printf 'warn: fs.inotify.max_user_instances < 512 — consider: sudo sysctl -w fs.inotify.max_user_instances=512\n' >&2
  fi
}

ensure_cluster() {
  if kind get clusters 2>/dev/null | grep -qx "${CLUSTER_NAME}"; then
    printf 'kind-up: cluster %s exists — skip create\n' "${CLUSTER_NAME}"
  else
    printf 'kind-up: creating Kind cluster %s (provider=%s)\n' "${CLUSTER_NAME}" "${KIND_EXPERIMENTAL_PROVIDER}"
    kind create cluster --name "${CLUSTER_NAME}" --config "${KIND_DIR}/kind-config.yaml"
  fi
  asf_kind_enable_loadbalancer "${CLUSTER_NAME}"
}

install_eg() {
  printf 'kind-up: Envoy Gateway %s\n' "${EG_CHART_VERSION}"
  helm upgrade --install eg oci://docker.io/envoyproxy/gateway-helm \
    --version "${EG_CHART_VERSION}" \
    --namespace envoy-gateway-system \
    --create-namespace \
    --kube-context "${CTX}" \
    -f "${GATEWAY_DIR}/values-eg.yaml" \
    --wait --timeout 5m
  kubectl --context "${CTX}" -n envoy-gateway-system \
    wait --timeout=5m --for=condition=Available deployment/envoy-gateway
  kubectl --context "${CTX}" apply -f "${GATEWAY_DIR}/gatewayclass.yaml"
}

install_kuadrant() {
  printf 'kind-up: Kuadrant operator %s\n' "${KUADRANT_CHART_VERSION}"
  helm repo add kuadrant https://kuadrant.io/helm-charts/ --force-update >/dev/null 2>&1 || true
  helm upgrade --install kuadrant-operator kuadrant/kuadrant-operator \
    --version "${KUADRANT_CHART_VERSION}" \
    --namespace kuadrant-system \
    --create-namespace \
    --kube-context "${CTX}" \
    --wait --timeout 5m
  kubectl --context "${CTX}" apply -f "${KUADRANT_DIR}/kuadrant.yaml"
  kubectl --context "${CTX}" -n kuadrant-system wait --timeout=3m \
    --for=condition=Ready kuadrant/kuadrant 2>/dev/null || \
    printf 'kind-up: Kuadrant Ready wait timed out — continue\n'
}

apply_gateway_policies() {
  kubectl --context "${CTX}" apply -f "${GATEWAY_DIR}/gateway.yaml"
  kubectl --context "${CTX}" apply -f "${KUADRANT_DIR}/ratelimitpolicy.yaml"
}

main() {
  prereq
  asf_ensure_cloud_provider_kind
  ensure_cluster
  install_eg
  install_kuadrant
  apply_gateway_policies

  cat <<EOF

kind-up: edge ready (PROFILE=kind-oss)

  Cluster:  ${CLUSTER_NAME} (context ${CTX})
  Gateway:  asf.demo.local:8080  (add to /etc/hosts → 127.0.0.1)
  RateLimit: 5 req / 10s on Gateway asf (expect HTTP 429 under burst)

Next:
  1. echo '127.0.0.1 asf.demo.local' | sudo tee -a /etc/hosts
  2. Start Ollama on host with a small model; set OSAI_INFERENCE_URL (see docs/workshop/kind-oss.md)
  3. Deploy factory + sample-app with HTTPRoute parentRefs → gateway-system/asf
  4. Optional: Langfuse for agent traces

EOF
}

main "$@"
