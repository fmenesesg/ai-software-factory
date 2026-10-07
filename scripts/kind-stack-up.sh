#!/usr/bin/env bash
# Full Kind OSS stack: edge + platform (Tekton/Argo/Jaeger) + factory + sample-app.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export KIND_EXPERIMENTAL_PROVIDER="${KIND_EXPERIMENTAL_PROVIDER:-podman}"
CLUSTER_NAME="${ASF_KIND_CLUSTER:-asf-kind}"
CTX="kind-${CLUSTER_NAME}"
FACTORY_IMAGE="${ASF_FACTORY_IMAGE:-localhost/asf-factory:kind}"
SAMPLE_IMAGE="${ASF_SAMPLE_IMAGE:-localhost/asf-sample-app:kind}"

cd "${ROOT}"

printf '==> 1/6 edge (Envoy Gateway + Kuadrant)\n'
"${ROOT}/scripts/kind-up.sh"

printf '==> 2/6 platform (registry, Tekton, Argo, Jaeger, OTel)\n'
chmod +x "${ROOT}/scripts/kind-stack-platform.sh"
"${ROOT}/scripts/kind-stack-platform.sh"

printf '==> 3/6 build factory image\n'
podman build -t "${FACTORY_IMAGE}" -f platform/kind/Containerfile.factory .

printf '==> 4/6 build sample-app image\n'
podman build -t "${SAMPLE_IMAGE}" -f platform/kind/Containerfile.sample-app .

printf '==> 5/6 load images into Kind\n'
# Podman → kind load via archive (rootless-friendly). Remove prior tars —
# podman save refuses to overwrite an existing docker-archive.
mkdir -p .tmp
rm -f .tmp/asf-factory.tar .tmp/asf-sample.tar
podman save "${FACTORY_IMAGE}" -o .tmp/asf-factory.tar
podman save "${SAMPLE_IMAGE}" -o .tmp/asf-sample.tar
kind load image-archive .tmp/asf-factory.tar --name "${CLUSTER_NAME}"
kind load image-archive .tmp/asf-sample.tar --name "${CLUSTER_NAME}"

printf '==> 6/6 apply workloads\n'
chmod +x platform/kind/apps/generate-workloads.sh
ASF_FACTORY_IMAGE="${FACTORY_IMAGE}" ./platform/kind/apps/generate-workloads.sh
kubectl --context "${CTX}" apply -f platform/kind/apps/factory-workloads.yaml
kubectl --context "${CTX}" apply -f platform/kind/apps/sample-app.yaml
# Re-apply Kind pipeline after ns exists
kubectl --context "${CTX}" apply -f platform/pipelines/tasks/sample-app-deploy-ephemeral-kind.yaml
kubectl --context "${CTX}" apply -f platform/pipelines/pipelines/sample-app-pr-kind.yaml

printf '==> waiting for deployments\n'
kubectl --context "${CTX}" -n asf-factory wait --for=condition=Available --timeout=420s \
  deployment --all

cat <<EOF

kind-stack-up: applied

  Hosts:     echo '127.0.0.1 asf.demo.local jaeger.asf.demo.local tekton.asf.demo.local chat.asf.demo.local' | sudo tee -a /etc/hosts
  Status:    http://asf.demo.local:8080/status/
  Jaeger:    http://jaeger.asf.demo.local:8080/
  Tekton:    http://tekton.asf.demo.local:8080/
  Chat:      http://chat.asf.demo.local:8080/
  Sample:    http://asf.demo.local:8080/
  Smoke:     ./scripts/kind-stack-smoke.sh

Demo trigger: create a GitHub Issue with label asf/run (needs real GITHUB_TOKEN in Secret).
Patch: kubectl -n asf-factory create secret generic asf-workshop-secrets \\
  --from-literal=GITHUB_TOKEN=\$GITHUB_TOKEN --dry-run=client -o yaml | kubectl apply -f -

EOF
