"""NAMESPACE_PREFIX scoping for OpenShift MCP."""

from __future__ import annotations


class OpenShiftSecurityError(ValueError):
    """Raised when an OpenShift operation escapes NAMESPACE_PREFIX."""


def assert_namespace_allowed(namespace: str, prefix: str) -> str:
    ns = (namespace or "").strip()
    pfx = (prefix or "").strip()
    if not pfx:
        raise OpenShiftSecurityError("NAMESPACE_PREFIX is required")
    if not ns:
        raise OpenShiftSecurityError("namespace is required")
    if ns.startswith("-") or ".." in ns or "/" in ns or " " in ns:
        raise OpenShiftSecurityError("invalid namespace form")
    if not ns.startswith(pfx):
        raise OpenShiftSecurityError(
            f"namespace outside NAMESPACE_PREFIX denied: {ns!r} (prefix {pfx!r})"
        )
    return ns
