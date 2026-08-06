"""Filesystem MCP unit tests — dry-run and allowlist."""

from __future__ import annotations

from pathlib import Path

import pytest

from mcp_filesystem.config import FilesystemMcpSettings
from mcp_filesystem.tools import FilesystemSecurityError, FilesystemTools


def test_read_write_under_allowlist(tmp_path: Path) -> None:
    (tmp_path / "sample-app").mkdir()
    settings = FilesystemMcpSettings(
        workspace_root=str(tmp_path),
        writable_roots="sample-app",
        dry_run=False,
    )
    tools = FilesystemTools(settings)
    result = tools.write("sample-app/hello.txt", "hi")
    assert result["ok"] is True
    assert (tmp_path / "sample-app" / "hello.txt").read_text() == "hi"
    read = tools.read("sample-app/hello.txt")
    assert read["content"] == "hi"


def test_dry_run_blocks_write(tmp_path: Path) -> None:
    (tmp_path / "sample-app").mkdir()
    settings = FilesystemMcpSettings(
        workspace_root=str(tmp_path),
        writable_roots="sample-app",
        dry_run=True,
    )
    tools = FilesystemTools(settings)
    result = tools.write("sample-app/hello.txt", "hi")
    assert result["blocked"] is True
    assert not (tmp_path / "sample-app" / "hello.txt").exists()


def test_write_outside_allowlist_denied(tmp_path: Path) -> None:
    (tmp_path / "secrets").mkdir()
    settings = FilesystemMcpSettings(
        workspace_root=str(tmp_path),
        writable_roots="sample-app",
        dry_run=False,
    )
    tools = FilesystemTools(settings)
    with pytest.raises(FilesystemSecurityError, match="allowlist"):
        tools.write("secrets/token.txt", "leak")


def test_red_docs_like_requirements_txt_outside_allowlist(tmp_path: Path) -> None:
    """RED: requirements.txt must not be written outside docs-like roots."""
    (tmp_path / "agents").mkdir()
    (tmp_path / "docs").mkdir()
    settings = FilesystemMcpSettings(
        workspace_root=str(tmp_path),
        writable_roots="agents,docs,sample-app",
        docs_like_roots="docs,sample-app",
        dry_run=False,
    )
    tools = FilesystemTools(settings)
    with pytest.raises(FilesystemSecurityError, match="docs-like"):
        tools.write("agents/requirements.txt", "flask==1.0")


def test_red_docs_like_readme_sh_outside_allowlist(tmp_path: Path) -> None:
    """RED: README.sh (docs disguised as script) denied outside allowlist."""
    (tmp_path / "platform").mkdir()
    settings = FilesystemMcpSettings(
        workspace_root=str(tmp_path),
        writable_roots="platform,docs,sample-app",
        docs_like_roots="docs,sample-app",
        dry_run=False,
    )
    tools = FilesystemTools(settings)
    with pytest.raises(FilesystemSecurityError, match="docs-like"):
        tools.write("platform/README.sh", "#!/bin/sh\necho pwned")


def test_red_docs_like_mdx_outside_allowlist(tmp_path: Path) -> None:
    """RED: MDX write outside docs/sample-app allowlist fails."""
    (tmp_path / "packages").mkdir()
    settings = FilesystemMcpSettings(
        workspace_root=str(tmp_path),
        writable_roots="packages,docs,sample-app",
        docs_like_roots="docs,sample-app",
        dry_run=False,
    )
    tools = FilesystemTools(settings)
    with pytest.raises(FilesystemSecurityError, match="docs-like"):
        tools.write("packages/note.mdx", "export const x = 1")


def test_docs_like_allowed_under_docs(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    settings = FilesystemMcpSettings(
        workspace_root=str(tmp_path),
        writable_roots="docs,sample-app",
        docs_like_roots="docs,sample-app",
        dry_run=False,
    )
    tools = FilesystemTools(settings)
    result = tools.write("docs/guide.mdx", "# Guide")
    assert result["ok"] is True
    assert (tmp_path / "docs" / "guide.mdx").read_text() == "# Guide"
