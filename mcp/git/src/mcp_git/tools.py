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
    assert_branch_name,
    assert_clone_dirname,
    assert_no_force_push,
    assert_remote_allowed,
    assert_repo_path_allowed,
    authenticated_https_remote,
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
                "name": "git_clone",
                "description": "Clone the allowed remote into workspace_root/<dirname>",
                "mutating": True,
            },
            {
                "name": "git_checkout",
                "description": "Create/switch branch (git checkout -B <branch>)",
                "mutating": True,
            },
            {
                "name": "git_add",
                "description": "Stage explicit paths (git add -- <paths>)",
                "mutating": True,
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
            if name == "git_clone":
                return self.clone(
                    dirname=str(args.get("dirname") or self.settings.github_repo),
                    remote_url=str(args.get("remote_url") or self.allowed_remote),
                )
            if name == "git_checkout":
                return self.checkout(
                    repo_path=args.get("repo_path", ""),
                    branch=str(args.get("branch") or ""),
                )
            if name == "git_add":
                return self.add(
                    repo_path=args.get("repo_path", ""),
                    paths=list(args.get("paths") or []),
                )
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

    def clone(self, *, dirname: str, remote_url: str) -> dict[str, Any]:
        name = assert_clone_dirname(dirname)
        assert_remote_allowed(remote_url, self.allowed_remote)
        dest = (self.workspace_root / name).resolve()
        try:
            dest.relative_to(self.workspace_root)
        except ValueError as exc:
            raise GitSecurityError("clone destination escapes workspace_root") from exc

        if dest.exists() and (dest / ".git").exists():
            return {"ok": True, "repo_path": str(dest), "already_cloned": True}

        if self.settings.dry_run:
            return {
                "ok": True,
                "dry_run": True,
                "blocked": True,
                "reason": "dry_run",
                "would_clone": {"remote_url": self.allowed_remote, "dirname": name},
            }

        self.workspace_root.mkdir(parents=True, exist_ok=True)
        auth = authenticated_https_remote(self.allowed_remote, self.settings.github_token)
        result = self.runner(["git", "clone", "--", auth, str(dest)], self.workspace_root)
        if result.returncode != 0:
            raise GitToolError(result.stderr or result.stdout or "git clone failed")
        # Reset origin to credential-free URL so `git remote -v` does not leak tokens.
        self.runner(["git", "remote", "set-url", "origin", self.allowed_remote], dest)
        return {"ok": True, "dry_run": False, "repo_path": str(dest), "already_cloned": False}

    def checkout(self, *, repo_path: str, branch: str) -> dict[str, Any]:
        path = assert_repo_path_allowed(repo_path, self.workspace_root)
        br = assert_branch_name(branch)
        if self.settings.dry_run:
            return {
                "ok": True,
                "dry_run": True,
                "blocked": True,
                "reason": "dry_run",
                "would_checkout": br,
            }
        # -B: create or reset branch to HEAD (workshop worktrees are disposable).
        result = self.runner(["git", "checkout", "-B", br], path)
        if result.returncode != 0:
            raise GitToolError(result.stderr or result.stdout or "git checkout failed")
        return {"ok": True, "dry_run": False, "branch": br, "repo_path": str(path)}

    def add(self, *, repo_path: str, paths: list[str]) -> dict[str, Any]:
        path = assert_repo_path_allowed(repo_path, self.workspace_root)
        cleaned: list[str] = []
        for p in paths:
            raw = str(p).strip()
            # Do NOT use str.lstrip("./") — it strips any combo of those chars
            # and would turn "../evil" into "evil".
            while raw.startswith("./"):
                raw = raw[2:]
            if not raw or raw.startswith("-") or raw.startswith("/") or ".." in Path(raw).parts:
                raise GitSecurityError(f"invalid path for git add: {p!r}")
            cleaned.append(raw)
        if not cleaned:
            raise GitSecurityError("paths required for git add")
        if self.settings.dry_run:
            return {
                "ok": True,
                "dry_run": True,
                "blocked": True,
                "reason": "dry_run",
                "would_add": cleaned,
            }
        result = self.runner(["git", "add", "--", *cleaned], path)
        if result.returncode != 0:
            raise GitToolError(result.stderr or result.stdout or "git add failed")
        return {"ok": True, "dry_run": False, "paths": cleaned, "repo_path": str(path)}

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

        # Ensure identity for Kind pods (no interactive git config).
        self.runner(["git", "config", "user.email", "asf-bot@localhost"], path)
        self.runner(["git", "config", "user.name", "ASF Bot"], path)
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
        # ref may be HEAD or HEAD:refs/heads/branch — validate branch side if present.
        push_ref = (ref or "HEAD").strip()
        if not push_ref or push_ref.startswith("-"):
            raise GitSecurityError(f"invalid ref: {ref!r}")
        if ":" in push_ref:
            local, remote = push_ref.split(":", 1)
            if local not in {"HEAD", "head"} and not local.startswith("refs/"):
                assert_branch_name(local)
            if remote.startswith("refs/heads/"):
                assert_branch_name(remote.removeprefix("refs/heads/"))
            elif remote:
                assert_branch_name(remote)

        if self.settings.dry_run:
            return {
                "ok": True,
                "dry_run": True,
                "blocked": True,
                "reason": "dry_run",
                "would_push": {"remote_url": self.allowed_remote, "ref": push_ref},
            }

        auth = authenticated_https_remote(self.allowed_remote, self.settings.github_token)
        argv = ["git", "push", "--", auth, push_ref]
        result = self.runner(argv, path)
        if result.returncode != 0:
            raise GitToolError(result.stderr or result.stdout or "git push failed")
        return {
            "ok": True,
            "dry_run": False,
            "remote_url": self.allowed_remote,
            "ref": push_ref,
            "stdout": result.stdout,
        }
