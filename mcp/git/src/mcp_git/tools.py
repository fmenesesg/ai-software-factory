"""Git MCP tool implementations (no shell-concat of model-controlled commands)."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from agent_sdk.otel import factory_span

from mcp_git.config import GitMcpSettings
from mcp_git.security import (
    GitSecurityError,
    assert_no_force_push,
    assert_remote_allowed,
    assert_repo_path_allowed,
    resolve_workspace_root,
)

Runner = Callable[[list[str], Path], subprocess.CompletedProcess[str]]


class GitToolError(RuntimeError):
    """Tool-level failure returned to MCP callers."""


def _default_runner(argv: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=cwd,
        check=False,
        text=True,
        capture_output=True,
    )


@dataclass
class GitTools:
    settings: GitMcpSettings
    runner: Runner = field(default=_default_runner)

    def __post_init__(self) -> None:
        self.workspace_root = resolve_workspace_root(self.settings.workspace_root)
        self.allowed_remote = self.settings.resolved_allowed_remote()

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "git_select_repo",
                "description": "Validate and select a repo path under workspace_root",
                "mutating": False,
            },
            {
                "name": "git_status",
                "description": "Show porcelain status for a selected repo",
                "mutating": False,
            },
            {
                "name": "git_commit",
                "description": "Commit only explicitly staged paths (refuses empty index)",
                "mutating": True,
            },
            {
                "name": "git_push",
                "description": "Push to the session-allowed remote (no --force)",
                "mutating": True,
            },
        ]

    def call(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        args = arguments or {}
        with factory_span(f"mcp.git.{name}", tool=name, agent="mcp-git"):
            if name == "git_select_repo":
                return self.select_repo(args.get("repo_path", ""))
            if name == "git_status":
                return self.status(args.get("repo_path", ""))
            if name == "git_commit":
                return self.commit(
                    repo_path=args.get("repo_path", ""),
                    message=str(args.get("message", "")),
                    staged_paths=list(args.get("staged_paths") or []),
                )
            if name == "git_push":
                return self.push(
                    repo_path=args.get("repo_path", ""),
                    remote_url=str(args.get("remote_url") or self.allowed_remote),
                    ref=str(args.get("ref") or "HEAD"),
                    force=bool(args.get("force", False)),
                    extra_args=list(args.get("extra_args") or []),
                )
            raise GitToolError(f"unknown tool: {name}")

    def select_repo(self, repo_path: str) -> dict[str, Any]:
        path = assert_repo_path_allowed(repo_path, self.workspace_root)
        return {"ok": True, "repo_path": str(path), "workspace_root": str(self.workspace_root)}

    def status(self, repo_path: str) -> dict[str, Any]:
        path = assert_repo_path_allowed(repo_path, self.workspace_root)
        result = self.runner(["git", "status", "--porcelain"], path)
        return {
            "ok": result.returncode == 0,
            "repo_path": str(path),
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }

    def commit(
        self,
        *,
        repo_path: str,
        message: str,
        staged_paths: list[str],
    ) -> dict[str, Any]:
        path = assert_repo_path_allowed(repo_path, self.workspace_root)
        if not message.strip():
            raise GitSecurityError("commit message is required")
        if not staged_paths:
            raise GitSecurityError("empty commit refused: staged_paths required")

        # Refuse success when index would be empty — check staged diff.
        staged = self.runner(["git", "diff", "--cached", "--name-only"], path)
        staged_names = {line.strip() for line in staged.stdout.splitlines() if line.strip()}
        requested = {p.strip().lstrip("./") for p in staged_paths if p.strip()}
        if not staged_names:
            raise GitSecurityError("empty commit refused: nothing staged in index")
        if not requested.issubset(staged_names) and staged_names.isdisjoint(requested):
            # Allow if caller listed paths that match staged; otherwise require overlap.
            raise GitSecurityError(
                "commit refused: staged_paths do not match intentional staged index entries"
            )

        if self.settings.dry_run:
            return {
                "ok": True,
                "dry_run": True,
                "blocked": True,
                "reason": "dry_run",
                "would_commit": sorted(staged_names & requested) or sorted(staged_names),
            }

        result = self.runner(["git", "commit", "-m", message, "--"] + sorted(requested), path)
        if result.returncode != 0:
            raise GitToolError(result.stderr or result.stdout or "git commit failed")
        return {
            "ok": True,
            "dry_run": False,
            "repo_path": str(path),
            "committed_paths": sorted(requested),
            "stdout": result.stdout,
        }

    def push(
        self,
        *,
        repo_path: str,
        remote_url: str,
        ref: str = "HEAD",
        force: bool = False,
        extra_args: list[str] | None = None,
    ) -> dict[str, Any]:
        path = assert_repo_path_allowed(repo_path, self.workspace_root)
        assert_remote_allowed(remote_url, self.allowed_remote)
        assert_no_force_push(force, extra_args)

        if self.settings.dry_run:
            return {
                "ok": True,
                "dry_run": True,
                "blocked": True,
                "reason": "dry_run",
                "would_push": {"remote_url": remote_url, "ref": ref},
            }

        # Structured argv only — never shell string concat.
        argv = ["git", "push", remote_url, ref]
        result = self.runner(argv, path)
        if result.returncode != 0:
            raise GitToolError(result.stderr or result.stdout or "git push failed")
        return {
            "ok": True,
            "dry_run": False,
            "remote_url": remote_url,
            "ref": ref,
            "stdout": result.stdout,
        }
