"""OpenShift MCP tools — namespace-scoped deploy/route/logs (injectable client)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from agent_sdk.otel import factory_span

from mcp_openshift.config import OpenShiftMcpSettings
from mcp_openshift.security import OpenShiftSecurityError, assert_namespace_allowed


class OpenShiftClient(Protocol):
    def apply_manifest(self, namespace: str, manifest: dict[str, Any]) -> dict[str, Any]: ...

    def get_route_url(self, namespace: str, name: str) -> str: ...

    def get_logs(self, namespace: str, name: str, *, tail: int = 100) -> str: ...

    def ensure_namespace(self, namespace: str) -> dict[str, Any]: ...


class OpenShiftToolError(RuntimeError):
    pass


@dataclass
class InMemoryOpenShiftClient:
    calls: list[dict[str, Any]] = field(default_factory=list)
    routes: dict[tuple[str, str], str] = field(default_factory=dict)
    logs: dict[tuple[str, str], str] = field(default_factory=dict)

    def ensure_namespace(self, namespace: str) -> dict[str, Any]:
        self.calls.append({"op": "ensure_namespace", "namespace": namespace})
        return {"ok": True, "namespace": namespace}

    def apply_manifest(self, namespace: str, manifest: dict[str, Any]) -> dict[str, Any]:
        self.calls.append({"op": "apply", "namespace": namespace, "manifest": manifest})
        return {"ok": True, "namespace": namespace}

    def get_route_url(self, namespace: str, name: str) -> str:
        self.calls.append({"op": "get_route", "namespace": namespace, "name": name})
        return self.routes.get((namespace, name), f"https://{name}.{namespace}.apps.example.com")

    def get_logs(self, namespace: str, name: str, *, tail: int = 100) -> str:
        self.calls.append({"op": "logs", "namespace": namespace, "name": name, "tail": tail})
        return self.logs.get((namespace, name), "")


@dataclass
class OpenShiftTools:
    settings: OpenShiftMcpSettings
    client: OpenShiftClient | None = None

    def __post_init__(self) -> None:
        if self.client is None:
            self.client = InMemoryOpenShiftClient()

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {"name": "oc_ensure_namespace", "description": "Create ns under prefix", "mutating": True},
            {"name": "oc_apply", "description": "Apply manifest in prefixed ns", "mutating": True},
            {"name": "oc_route_url", "description": "Resolve Route URL", "mutating": False},
            {"name": "oc_logs", "description": "Pod/deployment logs in prefixed ns", "mutating": False},
        ]

    def call(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        args = arguments or {}
        with factory_span(f"mcp.openshift.{name}", tool=name, agent="mcp-openshift"):
            if name == "oc_ensure_namespace":
                return self.ensure_namespace(args)
            if name == "oc_apply":
                return self.apply(args)
            if name == "oc_route_url":
                return self.route_url(args)
            if name == "oc_logs":
                return self.logs(args)
            raise OpenShiftToolError(f"unknown tool: {name}")

    def _ns(self, args: dict[str, Any]) -> str:
        return assert_namespace_allowed(
            str(args.get("namespace") or args.get("ns") or ""),
            self.settings.namespace_prefix,
        )

    def ensure_namespace(self, args: dict[str, Any]) -> dict[str, Any]:
        ns = self._ns(args)
        if self.settings.dry_run:
            return {"ok": True, "dry_run": True, "blocked": True, "reason": "dry_run", "namespace": ns}
        assert self.client is not None
        return {"ok": True, "dry_run": False, **self.client.ensure_namespace(ns)}

    def apply(self, args: dict[str, Any]) -> dict[str, Any]:
        ns = self._ns(args)
        manifest = args.get("manifest")
        if not isinstance(manifest, dict):
            raise OpenShiftSecurityError("manifest object is required")
        # Deny cross-namespace smuggling via metadata.
        meta_ns = (manifest.get("metadata") or {}).get("namespace")
        if meta_ns and meta_ns != ns:
            raise OpenShiftSecurityError("manifest.metadata.namespace must match allowed namespace")
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
        result = self.client.apply_manifest(ns, manifest)
        return {"ok": True, "dry_run": False, **result}

    def route_url(self, args: dict[str, Any]) -> dict[str, Any]:
        ns = self._ns(args)
        name = str(args.get("name") or "sample-app").strip()
        if not name:
            raise OpenShiftSecurityError("route name is required")
        assert self.client is not None
        url = self.client.get_route_url(ns, name)
        return {"ok": True, "namespace": ns, "name": name, "url": url}

    def logs(self, args: dict[str, Any]) -> dict[str, Any]:
        ns = self._ns(args)
        name = str(args.get("name") or "").strip()
        if not name:
            raise OpenShiftSecurityError("workload name is required")
        tail = int(args.get("tail") or 100)
        assert self.client is not None
        text = self.client.get_logs(ns, name, tail=tail)
        return {"ok": True, "namespace": ns, "name": name, "logs": text}
