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

# Rootless Podman + many Services: kube-proxy iptables hits
# "iptables-restore: Message too long" → ClusterIP/NodePort die → CCM :8080 empty reply.
ensure_kube_proxy_nftables() {
  local mode
  mode="$(kubectl --context "${CTX}" -n kube-system get cm kube-proxy \
    -o jsonpath='{.data.config\.conf}' 2>/dev/null | awk '/^mode:/{print $2; exit}')"
  if [[ "${mode}" == "nftables" ]]; then
    printf 'kind-up: kube-proxy already mode=nftables\n'
    return 0
  fi
  printf 'kind-up: switching kube-proxy to nftables (was %s)\n' "${mode:-unset}"
  kubectl --context "${CTX}" -n kube-system get cm kube-proxy -o jsonpath='{.data.config\.conf}' \
    | sed 's/^mode: .*/mode: nftables/' >/tmp/asf-kube-proxy.conf
  kubectl --context "${CTX}" -n kube-system create cm kube-proxy \
    --from-file=config.conf=/tmp/asf-kube-proxy.conf \
    --from-file=kubeconfig.conf=<(kubectl --context "${CTX}" -n kube-system get cm kube-proxy \
      -o jsonpath='{.data.kubeconfig\.conf}') \
    -o yaml --dry-run=client | kubectl --context "${CTX}" apply -f -
  rm -f /tmp/asf-kube-proxy.conf
  kubectl --context "${CTX}" -n kube-system delete po -l k8s-app=kube-proxy --wait=false
  kubectl --context "${CTX}" -n kube-system rollout status ds/kube-proxy --timeout=90s 2>/dev/null \
    || kubectl --context "${CTX}" -n kube-system wait --for=condition=Ready po -l k8s-app=kube-proxy --timeout=90s
}

ensure_cluster() {
  if kind get clusters 2>/dev/null | grep -qx "${CLUSTER_NAME}"; then
    printf 'kind-up: cluster %s exists — skip create\n' "${CLUSTER_NAME}"
  else
    printf 'kind-up: creating Kind cluster %s (provider=%s)\n' "${CLUSTER_NAME}" "${KIND_EXPERIMENTAL_PROVIDER}"
    kind create cluster --name "${CLUSTER_NAME}" --config "${KIND_DIR}/kind-config.yaml"
  fi
  ensure_kube_proxy_nftables
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
  # RateLimitPolicy deferred — Kuadrant stays installed as gateway control plane only.
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
  Edge:     Envoy Gateway + Kuadrant (RateLimitPolicy not applied by default)

Next:
  1. echo '127.0.0.1 asf.demo.local' | sudo tee -a /etc/hosts
  2. ./scripts/kind-stack-up.sh   # full factory + Issue poller

EOF
}

main "$@"
