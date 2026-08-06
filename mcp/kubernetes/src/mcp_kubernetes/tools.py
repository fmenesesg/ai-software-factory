"""Kubernetes MCP tools — get/apply within NAMESPACE_PREFIX namespaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from agent_sdk.otel import factory_span

from mcp_kubernetes.config import KubernetesMcpSettings
from mcp_kubernetes.security import KubernetesSecurityError, assert_namespace_allowed


class KubernetesClient(Protocol):
    def get(self, namespace: str, kind: str, name: str) -> dict[str, Any]: ...

    def apply(self, namespace: str, manifest: dict[str, Any]) -> dict[str, Any]: ...


class KubernetesToolError(RuntimeError):
    pass


@dataclass
class InMemoryKubernetesClient:
    objects: dict[tuple[str, str, str], dict[str, Any]] = field(default_factory=dict)
    calls: list[dict[str, Any]] = field(default_factory=list)

    def get(self, namespace: str, kind: str, name: str) -> dict[str, Any]:
        self.calls.append({"op": "get", "namespace": namespace, "kind": kind, "name": name})
        key = (namespace, kind.lower(), name)
        if key not in self.objects:
            raise KubernetesToolError(f"not found: {kind}/{name} in {namespace}")
        return self.objects[key]

    def apply(self, namespace: str, manifest: dict[str, Any]) -> dict[str, Any]:
        kind = str(manifest.get("kind") or "Unknown")
        name = str((manifest.get("metadata") or {}).get("name") or "unnamed")
        self.calls.append({"op": "apply", "namespace": namespace, "kind": kind, "name": name})
        self.objects[(namespace, kind.lower(), name)] = manifest
        return {"ok": True, "namespace": namespace, "kind": kind, "name": name}


@dataclass
class KubernetesTools:
    settings: KubernetesMcpSettings
    client: KubernetesClient | None = None

    def __post_init__(self) -> None:
        if self.client is None:
            self.client = InMemoryKubernetesClient()

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {"name": "k8s_get", "description": "Get a namespaced object", "mutating": False},
            {"name": "k8s_apply", "description": "Apply a namespaced manifest", "mutating": True},
        ]

    def call(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        args = arguments or {}
        with factory_span(f"mcp.kubernetes.{name}", tool=name, agent="mcp-kubernetes"):
            if name == "k8s_get":
                return self.get(args)
            if name == "k8s_apply":
                return self.apply(args)
            raise KubernetesToolError(f"unknown tool: {name}")

    def _ns(self, args: dict[str, Any]) -> str:
        return assert_namespace_allowed(
            str(args.get("namespace") or args.get("ns") or ""),
            self.settings.namespace_prefix,
        )

    def get(self, args: dict[str, Any]) -> dict[str, Any]:
        ns = self._ns(args)
        kind = str(args.get("kind") or "").strip()
        name = str(args.get("name") or "").strip()
        if not kind or not name:
            raise KubernetesSecurityError("kind and name are required")
        assert self.client is not None
        obj = self.client.get(ns, kind, name)
        return {"ok": True, "object": obj}

    def apply(self, args: dict[str, Any]) -> dict[str, Any]:
        ns = self._ns(args)
        manifest = args.get("manifest")
        if not isinstance(manifest, dict):
            raise KubernetesSecurityError("manifest object is required")
        meta_ns = (manifest.get("metadata") or {}).get("namespace")
        if meta_ns and meta_ns != ns:
            raise KubernetesSecurityError("manifest.metadata.namespace must match allowed namespace")
        if self.settings.dry_run:
            return {
                "ok": True,
                "dry_run": True,
                "blocked": True,
                "reason": "dry_run",
                "namespace": ns,
                "kind": manifest.get("kind"),
            }
        assert self.client is not None
        result = self.client.apply(ns, manifest)
        return {"ok": True, "dry_run": False, **result}
