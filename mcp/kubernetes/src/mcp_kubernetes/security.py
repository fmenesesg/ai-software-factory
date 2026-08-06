"""NAMESPACE_PREFIX scoping for Kubernetes MCP."""

from __future__ import annotations


class KubernetesSecurityError(ValueError):
    """Raised when a Kubernetes operation escapes NAMESPACE_PREFIX."""


def assert_namespace_allowed(namespace: str, prefix: str) -> str:
    ns = (namespace or "").strip()
    pfx = (prefix or "").strip()
    if not pfx:
        raise KubernetesSecurityError("NAMESPACE_PREFIX is required")
    if not ns:
        raise KubernetesSecurityError("namespace is required")
    if ns.startswith("-") or ".." in ns or "/" in ns or " " in ns:
        raise KubernetesSecurityError("invalid namespace form")
    if not ns.startswith(pfx):
        raise KubernetesSecurityError(
            f"namespace outside NAMESPACE_PREFIX denied: {ns!r} (prefix {pfx!r})"
        )
    return ns
