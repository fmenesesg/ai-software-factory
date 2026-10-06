# Kind OSS pins (AI Software Factory)

Aligned with KCD Argentina 2026 N-S pins where possible. Single cluster `asf-kind`.

| Component | Pin | Notes |
|-----------|-----|-------|
| kind | host install | `KIND_EXPERIMENTAL_PROVIDER=podman` |
| cloud-provider-kind | latest | **not MetalLB** |
| kindest/node | `v1.35.5@sha256:ce977ae6d65918d0b58a5f8b5e940429c2ce42fa3a5619ec2bbc60b949c0ac95` | Stable with EG/Kuadrant |
| Envoy Gateway Helm | `oci://docker.io/envoyproxy/gateway-helm` **v1.7.0** | `enableEnvoyPatchPolicy: true` |
| Kuadrant Operator | `kuadrant/kuadrant-operator` **1.5.2** | Limitador + Authorino via `Kuadrant` CR |
| Hostname | `asf.demo.local` | `/etc/hosts` → `127.0.0.1` |
| Gateway listener | **8080** | Rootless Podman cannot publish host `:80` via CCM |

## Out of this profile

Linkerd, Skupper, multi-site CoreDNS HA, Contour, MetalLB, OpenShift Routes as primary.
