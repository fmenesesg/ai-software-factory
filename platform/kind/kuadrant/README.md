# Kuadrant on Kind (PROFILE=kind-oss)

Reuses the **KCD Argentina N-S** pattern: Envoy Gateway + Kuadrant operator + RateLimitPolicy.

## Critical path

1. `scripts/kind-up.sh` installs EG + Kuadrant + Gateway `asf` + RateLimitPolicy.
2. Burst traffic → expect **HTTP 429** (5 req / 10s on Gateway).
3. `AuthPolicy` is optional (Authorino is installed via `Kuadrant` CR; not applied by default).

## Not included (by design)

- Multi-site CoreDNS / DNSPolicy HA (KCD BA west/east)
- Linkerd / Skupper
- Contour / MetalLB
