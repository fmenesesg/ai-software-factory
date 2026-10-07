"""RED: commit/push — refuse empty success, --force, wrong remote."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from mcp_git.config import GitMcpSettings
from mcp_git.security import GitSecurityError
from mcp_git.tools import GitTools


def _runner_factory(responses: dict[tuple[str, ...], subprocess.CompletedProcess[str]]):
    def runner(argv: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        key = tuple(argv)
        if key in responses:
            return responses[key]
        # fuzzy match on command prefix
        for resp_key, value in responses.items():
            if argv[: len(resp_key)] == list(resp_key):
                return value
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    return runner


def test_refuse_empty_commit_success(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    settings = GitMcpSettings(
        workspace_root=str(tmp_path),
        allowed_remote="https://github.com/fmenesesg/asf-demo-app.git",
        dry_run=False,
    )
    runner = _runner_factory(
        {
            ("git", "diff", "--cached", "--name-only"): subprocess.CompletedProcess(
                ["git", "diff", "--cached", "--name-only"], 0, stdout="", stderr=""
            )
        }
    )
    tools = GitTools(settings, runner=runner)
    with pytest.raises(GitSecurityError, match="empty commit refused"):
        tools.commit(repo_path=str(repo), message="msg", staged_paths=["a.py"])


def test_refuse_commit_without_staged_paths(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    settings = GitMcpSettings(workspace_root=str(tmp_path))
    tools = GitTools(settings)
    with pytest.raises(GitSecurityError, match="staged_paths required"):
        tools.commit(repo_path=str(repo), message="msg", staged_paths=[])


def test_deny_force_push(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    settings = GitMcpSettings(
        workspace_root=str(tmp_path),
        allowed_remote="https://github.com/fmenesesg/asf-demo-app.git",
    )
    tools = GitTools(settings)
    with pytest.raises(GitSecurityError, match="force"):
        tools.push(
            repo_path=str(repo),
            remote_url="https://github.com/fmenesesg/asf-demo-app.git",
            force=True,
        )


def test_deny_force_extra_args(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    settings = GitMcpSettings(
        workspace_root=str(tmp_path),
        allowed_remote="https://github.com/fmenesesg/asf-demo-app.git",
    )
    tools = GitTools(settings)
    with pytest.raises(GitSecurityError, match="force"):
        tools.push(
            repo_path=str(repo),
            remote_url="https://github.com/fmenesesg/asf-demo-app.git",
            extra_args=["--force-with-lease"],
        )


def test_deny_wrong_remote_on_push(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    settings = GitMcpSettings(
        workspace_root=str(tmp_path),
        allowed_remote="https://github.com/fmenesesg/asf-demo-app.git",
    )
    tools = GitTools(settings)
    with pytest.raises(GitSecurityError, match="wrong remote"):
        tools.push(repo_path=str(repo), remote_url="https://github.com/evil/repo.git")


def test_dry_run_blocks_push_write(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    settings = GitMcpSettings(
        workspace_root=str(tmp_path),
        allowed_remote="https://github.com/fmenesesg/asf-demo-app.git",
        dry_run=True,
    )
    called: list[list[str]] = []

    def runner(argv: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        called.append(argv)
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    tools = GitTools(settings, runner=runner)
    result = tools.push(
        repo_path=str(repo),
        remote_url="https://github.com/fmenesesg/asf-demo-app.git",
    )
    assert result["blocked"] is True
    assert result["dry_run"] is True
    assert called == []


def test_commit_dry_run_blocks_write(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    settings = GitMcpSettings(workspace_root=str(tmp_path), dry_run=True)
    runner = _runner_factory(
        {
            ("git", "diff", "--cached", "--name-only"): subprocess.CompletedProcess(
                ["git", "diff", "--cached", "--name-only"],
                0,
                stdout="packages/x.py\n",
                stderr="",
            )
        }
    )
    tools = GitTools(settings, runner=runner)
    result = tools.commit(
        repo_path=str(repo),
        message="feat: x",
        staged_paths=["packages/x.py"],
    )
    assert result["dry_run"] is True
    assert result["blocked"] is True
