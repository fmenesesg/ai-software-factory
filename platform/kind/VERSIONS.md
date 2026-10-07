# Kind OSS pins (AI Software Factory)

Aligned with KCD Argentina 2026 N-S pins where possible. Single cluster `asf-kind`.

| Component | Pin | Notes |
|-----------|-----|-------|
| kind | host install | `KIND_EXPERIMENTAL_PROVIDER=podman` |
| cloud-provider-kind | latest | **not MetalLB** |
| kindest/node | `v1.35.5@sha256:ce977ae6d65918d0b58a5f8b5e940429c2ce42fa3a5619ec2bbc60b949c0ac95` | Stable with EG/Kuadrant |
| Envoy Gateway Helm | `oci://docker.io/envoyproxy/gateway-helm` **v1.7.0** | `enableEnvoyPatchPolicy: true` (edge left stable; EG 1.9+ needs separate validation) |
| Kuadrant Operator | `kuadrant/kuadrant-operator` **1.5.2** | Limitador + Authorino via `Kuadrant` CR |
| Hostnames | `asf.demo.local`, `*.asf.demo.local` | `/etc/hosts` → `127.0.0.1` (jaeger / tekton / chat) |
| Gateway listener | **8080** | Rootless Podman cannot publish host `:80` via CCM |
| Tekton Pipelines | **v1.17.0** | `scripts/kind-stack-platform.sh` via `infra.tekton.dev` |
| Tekton Dashboard | **v0.73.0** | `tekton.asf.demo.local:8080` |
| Argo CD | **v3.5.4** | upstream `manifests/install.yaml` (port-forward UI) |
| Jaeger | **2.22.0** | `jaegertracing/jaeger:2.22.0`; UI `jaeger.asf.demo.local:8080`; native OTLP |
| kubectl (Tekton task) | `alpine/k8s:1.33.13` | Preloaded into Kind by `kind-stack-platform.sh` |
| Open WebUI | **v0.11.4** | `chat.asf.demo.local:8080` → inference gateway |
| OTel collector contrib | **0.162.0** | OTLP → Jaeger; debug exporter |
| Registry | **registry:2.8.3** | namespace `asf-registry` |

## Out of this profile

Linkerd, Skupper, multi-site CoreDNS HA, Contour, MetalLB, OpenShift Routes as primary, Langfuse self-host (too heavy for Kind; see ADR-014).
