"""Filesystem MCP tools with path allowlisting and dry-run write blocking."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_sdk.otel import factory_span

from mcp_filesystem.config import FilesystemMcpSettings

# Threat-matrix docs-like paths — denied outside docs/sample-app allowlist.
_DOCS_LIKE_NAMES = frozenset({"requirements.txt", "readme.sh"})
_DOCS_LIKE_SUFFIXES = (".mdx",)


class FilesystemToolError(RuntimeError):
    pass


class FilesystemSecurityError(ValueError):
    pass


def is_docs_like_path(path: Path) -> bool:
    """Return True for requirements.txt, README.sh, and *.mdx paths."""
    name = path.name.lower()
    if name in _DOCS_LIKE_NAMES:
        return True
    return any(name.endswith(suffix) for suffix in _DOCS_LIKE_SUFFIXES)


@dataclass
class FilesystemTools:
    settings: FilesystemMcpSettings

    def __post_init__(self) -> None:
        root = Path(self.settings.workspace_root).expanduser()
        if not root.is_absolute():
            root = (Path.cwd() / root).resolve()
        else:
            root = root.resolve()
        self.workspace_root = root
        self.writable_roots = [
            (self.workspace_root / rel).resolve() for rel in self.settings.writable_root_list()
        ]
        self.docs_like_roots = [
            (self.workspace_root / rel).resolve() for rel in self.settings.docs_like_root_list()
        ]

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {"name": "fs_read", "description": "Read a file under workspace_root", "mutating": False},
            {"name": "fs_write", "description": "Write a file under writable allowlist", "mutating": True},
            {"name": "fs_list", "description": "List a directory under workspace_root", "mutating": False},
        ]

    def call(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        args = arguments or {}
        with factory_span(f"mcp.filesystem.{name}", tool=name, agent="mcp-filesystem"):
            if name == "fs_read":
                return self.read(str(args.get("path", "")))
            if name == "fs_write":
                return self.write(str(args.get("path", "")), str(args.get("content", "")))
            if name == "fs_list":
                return self.list_dir(str(args.get("path", ".")))
            raise FilesystemToolError(f"unknown tool: {name}")

    def _resolve_under_workspace(self, path: str) -> Path:
        raw = path.strip()
        if not raw or ".." in Path(raw).parts:
            raise FilesystemSecurityError("path escape denied")
        candidate = Path(raw)
        if candidate.is_absolute():
            resolved = candidate.resolve()
        else:
            resolved = (self.workspace_root / candidate).resolve()
        try:
            resolved.relative_to(self.workspace_root)
        except ValueError as exc:
            raise FilesystemSecurityError("path escapes workspace_root") from exc
        return resolved

    def _assert_writable(self, path: Path) -> None:
        for root in self.writable_roots:
            try:
                path.relative_to(root)
                return
            except ValueError:
                continue
        raise FilesystemSecurityError(f"write outside allowlist denied: {path}")

    def _assert_docs_like_allowed(self, path: Path) -> None:
        if not is_docs_like_path(path):
            return
        for root in self.docs_like_roots:
            try:
                path.relative_to(root)
                return
            except ValueError:
                continue
        raise FilesystemSecurityError(f"docs-like path outside allowlist denied: {path}")

    def read(self, path: str) -> dict[str, Any]:
        target = self._resolve_under_workspace(path)
        if not target.is_file():
            raise FilesystemToolError(f"not a file: {target}")
        return {"ok": True, "path": str(target), "content": target.read_text(encoding="utf-8")}

    def write(self, path: str, content: str) -> dict[str, Any]:
        target = self._resolve_under_workspace(path)
        self._assert_writable(target)
        self._assert_docs_like_allowed(target)
        if self.settings.dry_run:
            return {
                "ok": True,
                "dry_run": True,
                "blocked": True,
                "reason": "dry_run",
                "would_write": str(target),
                "bytes": len(content.encode("utf-8")),
            }
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return {"ok": True, "dry_run": False, "path": str(target), "bytes": len(content.encode("utf-8"))}

    def list_dir(self, path: str) -> dict[str, Any]:
        target = self._resolve_under_workspace(path)
        if not target.is_dir():
            raise FilesystemToolError(f"not a directory: {target}")
        entries = sorted(p.name for p in target.iterdir())
        return {"ok": True, "path": str(target), "entries": entries}
