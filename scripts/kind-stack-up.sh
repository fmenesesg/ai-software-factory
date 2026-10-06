#!/usr/bin/env bash
# Full Kind OSS stack: edge (EG+Kuadrant) + factory image + workloads + sample-app.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export KIND_EXPERIMENTAL_PROVIDER="${KIND_EXPERIMENTAL_PROVIDER:-podman}"
CLUSTER_NAME="${ASF_KIND_CLUSTER:-asf-kind}"
CTX="kind-${CLUSTER_NAME}"
FACTORY_IMAGE="${ASF_FACTORY_IMAGE:-localhost/asf-factory:kind}"
SAMPLE_IMAGE="${ASF_SAMPLE_IMAGE:-localhost/asf-sample-app:kind}"

cd "${ROOT}"

printf '==> 1/5 edge (Envoy Gateway + Kuadrant)\n'
"${ROOT}/scripts/kind-up.sh"

printf '==> 2/5 build factory image\n'
podman build -t "${FACTORY_IMAGE}" -f platform/kind/Containerfile.factory .

printf '==> 3/5 build sample-app image\n'
podman build -t "${SAMPLE_IMAGE}" -f platform/kind/Containerfile.sample-app .

printf '==> 4/5 load images into Kind\n'
# Podman → kind load via archive (rootless-friendly). Remove prior tars —
# podman save refuses to overwrite an existing docker-archive.
mkdir -p .tmp
rm -f .tmp/asf-factory.tar .tmp/asf-sample.tar
podman save "${FACTORY_IMAGE}" -o .tmp/asf-factory.tar
podman save "${SAMPLE_IMAGE}" -o .tmp/asf-sample.tar
kind load image-archive .tmp/asf-factory.tar --name "${CLUSTER_NAME}"
kind load image-archive .tmp/asf-sample.tar --name "${CLUSTER_NAME}"

printf '==> 5/5 apply workloads\n'
chmod +x platform/kind/apps/generate-workloads.sh
ASF_FACTORY_IMAGE="${FACTORY_IMAGE}" ./platform/kind/apps/generate-workloads.sh
kubectl --context "${CTX}" apply -f platform/kind/apps/factory-workloads.yaml
kubectl --context "${CTX}" apply -f platform/kind/apps/sample-app.yaml

printf '==> waiting for deployments\n'
kubectl --context "${CTX}" -n asf-factory wait --for=condition=Available --timeout=420s \
  deployment --all

cat <<EOF

kind-stack-up: applied

  Hosts:   echo '127.0.0.1 asf.demo.local' | sudo tee -a /etc/hosts
  Status:  http://asf.demo.local:8080/status/
  Sample:  http://asf.demo.local:8080/
  Smoke:   ./scripts/kind-stack-smoke.sh

Inference is GATEWAY_STUB_MODE=true by default (works without Ollama).
To use host Ollama later: patch ConfigMap asf-kind-config and set GATEWAY_STUB_MODE=false.

EOF
