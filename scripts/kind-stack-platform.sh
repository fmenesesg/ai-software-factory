#!/usr/bin/env bash
# Install Kind OSS platform extras: registry, Tekton(+Dashboard), Argo CD, Jaeger, Open WebUI, OTel.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export KIND_EXPERIMENTAL_PROVIDER="${KIND_EXPERIMENTAL_PROVIDER:-podman}"
CLUSTER_NAME="${ASF_KIND_CLUSTER:-asf-kind}"
CTX="kind-${CLUSTER_NAME}"

# Latest upstream pins (see platform/kind/VERSIONS.md)
TEKTON_VERSION="${TEKTON_VERSION:-v1.17.0}"
TEKTON_DASHBOARD_VERSION="${TEKTON_DASHBOARD_VERSION:-v0.73.0}"
ARGOCD_VERSION="${ARGOCD_VERSION:-v3.5.4}"
TEKTON_RELEASE_BASE="${TEKTON_RELEASE_BASE:-https://infra.tekton.dev/tekton-releases}"

die() { printf 'error: %s\n' "$*" >&2; exit 1; }

kubectl --context "${CTX}" get ns >/dev/null 2>&1 || die "cluster context ${CTX} not ready"

# Ensure apex + *.asf.demo.local listeners before UI HTTPRoutes.
kubectl --context "${CTX}" apply -f "${ROOT}/platform/kind/gateway/gateway.yaml"

printf '==> registry\n'
kubectl --context "${CTX}" apply -f "${ROOT}/platform/kind/registry/registry.yaml"
kubectl --context "${CTX}" -n asf-registry wait --for=condition=Available --timeout=180s deploy/registry || true

printf '==> Tekton Pipelines %s\n' "${TEKTON_VERSION}"
kubectl --context "${CTX}" apply --server-side --force-conflicts -f \
  "${TEKTON_RELEASE_BASE}/pipeline/previous/${TEKTON_VERSION}/release.yaml"
kubectl --context "${CTX}" -n tekton-pipelines wait --for=condition=Available --timeout=300s \
  deployment --all || true

printf '==> Tekton Dashboard %s\n' "${TEKTON_DASHBOARD_VERSION}"
kubectl --context "${CTX}" apply --server-side --force-conflicts -f \
  "${TEKTON_RELEASE_BASE}/dashboard/previous/${TEKTON_DASHBOARD_VERSION}/release-full.yaml"
kubectl --context "${CTX}" -n tekton-pipelines wait --for=condition=Available --timeout=300s \
  deploy/tekton-dashboard || true
# release-full also creates an empty tekton-dashboard namespace; the Deployment lives in tekton-pipelines.
kubectl --context "${CTX}" apply -f "${ROOT}/platform/kind/tekton/dashboard-route.yaml"

printf '==> Tekton Kind tasks/pipeline\n'
kubectl --context "${CTX}" get ns asf-factory >/dev/null 2>&1 || \
  kubectl --context "${CTX}" create ns asf-factory
# Preload kubectl image used by ephemeral Task (Kind nodes often cannot pull mid-run).
KUBECTL_TASK_IMAGE="${KUBECTL_TASK_IMAGE:-docker.io/alpine/k8s:1.33.13}"
printf 'kind-stack-platform: ensuring %s in Kind\n' "${KUBECTL_TASK_IMAGE}"
mkdir -p "${ROOT}/.tmp"
rm -f "${ROOT}/.tmp/kubectl-task.tar"
podman pull "${KUBECTL_TASK_IMAGE}"
podman save "${KUBECTL_TASK_IMAGE}" -o "${ROOT}/.tmp/kubectl-task.tar"
kind load image-archive "${ROOT}/.tmp/kubectl-task.tar" --name "${CLUSTER_NAME}"
kubectl --context "${CTX}" apply -f "${ROOT}/platform/pipelines/tasks/sample-app-deploy-ephemeral-kind.yaml"
kubectl --context "${CTX}" apply -f "${ROOT}/platform/pipelines/pipelines/sample-app-pr-kind.yaml"
kubectl --context "${CTX}" apply -f "${ROOT}/platform/kind/apps/orchestrator-rbac.yaml"
kubectl --context "${CTX}" apply -f "${ROOT}/platform/kind/apps/tekton-ephemeral-rbac.yaml"

printf '==> Argo CD %s\n' "${ARGOCD_VERSION}"
kubectl --context "${CTX}" create namespace argocd --dry-run=client -o yaml | kubectl --context "${CTX}" apply -f -
# Server-side apply: Argo CRD annotations exceed client-side apply size limits.
kubectl --context "${CTX}" apply --server-side --force-conflicts -n argocd -f \
  "https://raw.githubusercontent.com/argoproj/argo-cd/${ARGOCD_VERSION}/manifests/install.yaml"
kubectl --context "${CTX}" -n argocd wait --for=condition=Available --timeout=360s \
  deployment/argocd-server || true
kubectl --context "${CTX}" apply -f "${ROOT}/platform/gitops/argo/application-stub.yaml" || true

printf '==> Jaeger + OTel\n'
# Drop leftover Langfuse objects from older stacks (ignore if absent).
kubectl --context "${CTX}" -n asf-observability delete deploy/langfuse-web deploy/langfuse-db \
  svc/langfuse-web svc/langfuse-db secret/langfuse-secrets httproute/langfuse --ignore-not-found || true
kubectl --context "${CTX}" apply -f "${ROOT}/platform/kind/jaeger/jaeger.yaml"
kubectl --context "${CTX}" apply -f "${ROOT}/platform/kind/otel/collector.yaml"
kubectl --context "${CTX}" -n asf-observability wait --for=condition=Available --timeout=300s \
  deploy/jaeger deploy/otel-collector || true

printf '==> Open WebUI (chat → inference gateway)\n'
kubectl --context "${CTX}" apply -f "${ROOT}/platform/kind/open-webui/open-webui.yaml"
kubectl --context "${CTX}" -n asf-chat wait --for=condition=Available --timeout=360s \
  deploy/open-webui || true

printf 'kind-stack-platform: done (registry, Tekton+Dashboard, Argo CD, Jaeger, Open WebUI, OTel)\n'
