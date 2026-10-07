"""Threat-matrix guards for git repository selection and push/commit args."""

from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


class GitSecurityError(ValueError):
    """Raised when a git operation violates workshop security policy."""


_BRANCH_RE = re.compile(r"^[A-Za-z0-9._][A-Za-z0-9._/-]*$")


def resolve_workspace_root(workspace_root: str) -> Path:
    """Resolve and normalize workspace root; reject empty / relative escapes."""
    if not workspace_root or not str(workspace_root).strip():
        raise GitSecurityError("workspace_root is required")
    raw = str(workspace_root).strip()
    if raw.startswith("-"):
        raise GitSecurityError("workspace_root must not look like a CLI flag")
    # Reject explicit git -C style injection attempts in the path string.
    if " -C " in f" {raw} " or raw.startswith("-C") or "/-C/" in raw.replace("\\", "/"):
        raise GitSecurityError("git -C style path injection is denied")
    path = Path(raw).expanduser()
    if not path.is_absolute():
        # Relative roots are only allowed when they resolve under cwd without '..' climb.
        if ".." in path.parts:
            raise GitSecurityError("relative workspace_root with '..' is denied")
        path = (Path.cwd() / path).resolve()
    else:
        path = path.resolve()
    return path


def assert_repo_path_allowed(repo_path: str | Path, workspace_root: Path) -> Path:
    """Ensure repo_path is absolute, under workspace_root, and not a -C escape."""
    raw = str(repo_path).strip()
    if not raw:
        raise GitSecurityError("repo_path is required")
    if raw.startswith("-") or " -C " in f" {raw} ":
        raise GitSecurityError("repo path CLI-flag / -C injection is denied")
    if not os.path.isabs(raw):
        raise GitSecurityError("relative repo_path is denied; use an absolute path under workspace_root")
    path = Path(raw).resolve()
    try:
        path.relative_to(workspace_root.resolve())
    except ValueError as exc:
        raise GitSecurityError(
            f"repo_path escapes workspace_root ({workspace_root}): {path}"
        ) from exc
    return path


def _norm_remote(url: str) -> str:
    """Normalize remote for comparison (strip credentials + optional .git)."""
    raw = (url or "").strip().rstrip("/")
    parts = urlsplit(raw)
    # Drop userinfo so tokenized push URLs still match the allowlist.
    host_path = urlunsplit((parts.scheme.lower(), parts.hostname or "", parts.path, "", ""))
    u = host_path.lower()
    if u.endswith(".git"):
        u = u[:-4]
    return u


def assert_remote_allowed(remote_url: str, allowed_remote: str) -> str:
    """Push only to the session-configured remote."""
    candidate = (remote_url or "").strip()
    expected = allowed_remote.strip()
    if _norm_remote(candidate) != _norm_remote(expected):
        raise GitSecurityError(
            f"wrong remote denied: got {remote_url!r}, allowed {allowed_remote!r}"
        )
    return candidate


def assert_branch_name(branch: str) -> str:
    """Allow only simple branch names (no flags / shell metacharacters)."""
    raw = (branch or "").strip()
    if not raw or raw.startswith("-") or ".." in raw or raw.startswith("/"):
        raise GitSecurityError(f"invalid branch name: {branch!r}")
    if not _BRANCH_RE.match(raw):
        raise GitSecurityError(f"invalid branch name: {branch!r}")
    return raw


_DIRNAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def assert_clone_dirname(dirname: str) -> str:
    """Single path segment under workspace_root for git clone destination."""
    raw = (dirname or "").strip().strip("/")
    if not raw or "/" in raw or ".." in raw or raw.startswith("-") or not _DIRNAME_RE.match(raw):
        raise GitSecurityError(f"invalid clone dirname: {dirname!r}")
    return raw


def authenticated_https_remote(remote_url: str, token: str | None) -> str:
    """Embed PAT for HTTPS push/clone without accepting token from model args."""
    clean = remote_url.strip()
    if not token or not token.strip():
        return clean
    parts = urlsplit(clean)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        return clean
    # x-access-token is GitHub's documented non-interactive HTTPS form.
    netloc = f"x-access-token:{token.strip()}@{parts.hostname}"
    if parts.port:
        netloc = f"{netloc}:{parts.port}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def assert_no_force_push(force: bool | None, extra_args: list[str] | None = None) -> None:
    if force:
        raise GitSecurityError("--force push is denied")
    for arg in extra_args or []:
        lowered = arg.strip().lower()
        if lowered in {"--force", "-f", "--force-with-lease"}:
            raise GitSecurityError(f"force push argument denied: {arg}")
