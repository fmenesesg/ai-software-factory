# Kind OSS workshop path (PROFILE=kind-oss)

Laptop-local AI Software Factory on **Kind + Podman** with **no paid Red Hat products**.

## Stack

| Layer | Choice |
|-------|--------|
| Cluster | Kind `asf-kind` (`KIND_EXPERIMENTAL_PROVIDER=podman`) |
| LoadBalancer | `cloud-provider-kind --enable-lb-port-mapping` |
| Edge | Envoy Gateway + Kuadrant (RateLimitPolicy → 429 wow) |
| Inference | Ollama on **host**, small models |
| Agent viz | Langfuse (install separately; MIT) |
| Agents / Tekton / Argo | Full set when RAM allows (see ADR-014) |

Pattern reused from **KCD Argentina 2026** N-S (`Envoy Gateway + Kuadrant`), single cluster only.

## Prerequisites

```bash
# CLIs
kind kubectl helm cloud-provider-kind podman

# Optional but recommended on Linux
sudo sysctl -w fs.inotify.max_user_instances=512

go install sigs.k8s.io/cloud-provider-kind@latest
# ensure $(go env GOPATH)/bin is on PATH
```

## Bring up edge only

```bash
export KIND_EXPERIMENTAL_PROVIDER=podman
./scripts/kind-up.sh
echo '127.0.0.1 asf.demo.local' | sudo tee -a /etc/hosts
```

## Bring up full local stack (edge + agents + sample-app)

```bash
export KIND_EXPERIMENTAL_PROVIDER=podman
./scripts/kind-stack-up.sh
# first run builds images (several minutes)
./scripts/kind-stack-smoke.sh
```

Open **http://asf.demo.local:8080/status/** for the agent health board.  
Inference defaults to **stub mode** (no Ollama required). Sample app root: **http://asf.demo.local:8080/**.

Tear down:

```bash
./scripts/kind-stack-down.sh           # workloads only
./scripts/kind-stack-down.sh --cluster # + delete asf-kind
```

Burst test (after EXTERNAL-IP / port-map is ready):

```bash
for i in $(seq 1 12); do
  curl -sS -o /dev/null -w "%{http_code}\n" -H 'Host: asf.demo.local' http://127.0.0.1:8080/ || true
done
# Expect mix of failures until backends exist; once HTTPRoute→sample-app is up, expect 200 then 429.
```

## Inference (small models)

```bash
# Host Ollama example
ollama pull granite3.1-moe:1b   # or any small instruct tag you prefer
ollama serve

# Workshop env (example)
export PROFILE=kind-oss
export GATEWAY_STUB_MODE=false
export OSAI_INFERENCE_URL=http://host.containers.internal:11434/v1
export OSAI_MODEL_ID=granite3.1-moe:1b
```

From pods inside Kind, `host.containers.internal` (Podman) reaches the host Ollama. If that hostname is missing, use your host LAN IP.

## Sample-app HTTPRoute

```bash
helm upgrade --install sample-app ./sample-app/helm \
  -n asf-workshop-demo --create-namespace \
  --set route.enabled=false \
  --set httproute.enabled=true \
  --set httproute.hostname=asf.demo.local \
  --set httproute.pathPrefix=/
```

## Tear down

```bash
./scripts/kind-down.sh   # only deletes asf-kind; never kind-cluster / kind-west
```

## References

- ADR-014: `docs/architecture/adr/014-kind-oss.md`
- Pins: `platform/kind/VERSIONS.md`
- Profile: `platform/profiles/kind-oss.yaml`
