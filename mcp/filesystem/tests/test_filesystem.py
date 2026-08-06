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
