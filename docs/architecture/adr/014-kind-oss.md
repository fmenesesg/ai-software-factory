# ADR-014: Kind OSS local platform (Envoy Gateway + Kuadrant)

**Status:** Accepted  
**Date:** 2026-10-06  
**Updated:** 2026-10-07  
**Engram:** `sdd/ai-software-factory/adr-014`

## Context

The workshop MVP targeted on-demand OpenShift + OpenShift AI. Presenters also need a **laptop-local** path with **no paid Red Hat products**, using Kind on Podman Desktop, full agent mesh when RAM allows, and **small open-weight models**.

KCD Argentina 2026 already proved Envoy Gateway + Kuadrant on Kind+Podman with `cloud-provider-kind` (not MetalLB, not Contour as Kuadrant data plane).

## Decision

1. Add **`PROFILE=kind-oss`** as a first-class local profile alongside `minimal|standard|full`.
2. North-south edge for Kind: **Envoy Gateway** + **Kuadrant** (RateLimitPolicy required wow; AuthPolicy optional), patterns reused from KCD BA N-S.
3. LoadBalancer: **`cloud-provider-kind --enable-lb-port-mapping`** (not MetalLB; not Contour-for-Kuadrant).
4. Single Kind cluster name: **`asf-kind`** (never mutate unrelated `kind-cluster` / `kind-west`).
5. Inference: **Ollama (or compatible) on the host** with **small models**; gateway remains OpenAI-compatible (`GATEWAY_STUB_MODE=false`, `OSAI_INFERENCE_URL` → local).
6. Agent visualization: **Jaeger 2** (Apache-2.0, official `jaegertracing/jaeger` image, native OTLP) + status board + `/orch/v1/runs`. Agents export OTLP only; collector forwards to Jaeger — **no custom exporters**.
7. **Rejected for Kind:** self-hosted Langfuse 2.x (stale) or Langfuse 3/4 (needs worker + Postgres + Redis + ClickHouse + object storage). **Phoenix** (Arize) is LLM-native but ELv2 — skip unless license is accepted later.
8. **Out of Kind OSS scope:** OpenShift AI, RHDH product, RHACS/TAS product, Quay-required, Contour-as-Kuadrant-provider, Linkerd, Skupper, multi-site DNS HA (unless later ADR).
9. Sample-app exposes **HTTPRoute** (Gateway API) when `httproute.enabled`; OpenShift **Route** remains optional for OCP profiles.

## Consequences

- Presenters can rehearse the full factory narrative on a laptop without OCP.
- Demo wow includes Kuadrant **429** on inference paths (tight RateLimitPolicy).
- Resource pressure is managed via small models + optional agent request limits; docs describe 32 GB as full-stack baseline.
- OCP workshop path (`PROFILE=standard|full`) remains valid; Kind is additive, not a replacement of the RH narrative when a cluster is available.
- Trace UI is standard distributed tracing (Jaeger), not LLM prompt/score dashboards.
