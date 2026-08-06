"""RED: Git repository selection — reject relative / -C / wrong remote."""

from __future__ import annotations

from pathlib import Path

import pytest

from mcp_git.config import GitMcpSettings
from mcp_git.security import GitSecurityError, assert_remote_allowed, assert_repo_path_allowed, resolve_workspace_root
from mcp_git.tools import GitTools


def test_reject_relative_repo_path(tmp_path: Path) -> None:
    settings = GitMcpSettings(workspace_root=str(tmp_path), github_owner="fmenesesg", github_repo="ai-software-factory")
    tools = GitTools(settings)
    with pytest.raises(GitSecurityError, match="relative repo_path"):
        tools.select_repo("../escape")


def test_reject_git_dash_c_injection(tmp_path: Path) -> None:
    settings = GitMcpSettings(workspace_root=str(tmp_path))
    tools = GitTools(settings)
    with pytest.raises(GitSecurityError):
        tools.select_repo(f"-C {tmp_path / 'other'}")


def test_reject_repo_outside_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    settings = GitMcpSettings(workspace_root=str(workspace))
    tools = GitTools(settings)
    with pytest.raises(GitSecurityError, match="escapes workspace_root"):
        tools.select_repo(str(outside))


def test_reject_wrong_remote(tmp_path: Path) -> None:
    allowed = "https://github.com/fmenesesg/ai-software-factory.git"
    with pytest.raises(GitSecurityError, match="wrong remote"):
        assert_remote_allowed("https://evil.example/repo.git", allowed)


def test_accept_allowed_repo_under_workspace(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    settings = GitMcpSettings(workspace_root=str(tmp_path))
    tools = GitTools(settings)
    result = tools.select_repo(str(repo))
    assert result["ok"] is True
    assert Path(result["repo_path"]) == repo.resolve()


def test_resolve_workspace_rejects_relative_climb(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(GitSecurityError, match="\\.\\."):
        resolve_workspace_root("../outside")


def test_assert_repo_path_requires_absolute(tmp_path: Path) -> None:
    with pytest.raises(GitSecurityError, match="relative"):
        assert_repo_path_allowed("subdir/repo", tmp_path)
