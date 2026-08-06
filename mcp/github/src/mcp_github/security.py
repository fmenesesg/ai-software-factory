"""Threat-matrix guards for GitHub PR tool arguments (no shell concat / spoof)."""

from __future__ import annotations

import re

_ENV_INJECTION_RE = re.compile(
    r"(?:^|[;&|`$]|\bexport\b|\benv\b).*(?:GITHUB_|GH_|TOKEN=|Authorization)",
    re.IGNORECASE,
)
_SHELL_META_RE = re.compile(r"[;&|`$]|\$\(|\n")


class GitHubSecurityError(ValueError):
    """Raised when PR/issue arguments violate workshop security policy."""


def assert_no_shell_payload(value: str, *, field: str) -> str:
    """Reject shell metacharacters and env-injection attempts in structured fields."""
    if _SHELL_META_RE.search(value):
        raise GitHubSecurityError(f"{field}: shell metacharacters / concat denied")
    if _ENV_INJECTION_RE.search(value):
        raise GitHubSecurityError(f"{field}: env / token injection denied")
    return value


def assert_owned_head_ref(
    head: str,
    *,
    owner: str,
    repo: str,
) -> str:
    """Deny cross-repo --head spoof; head must be branch or owner:branch for owned repo."""
    raw = assert_no_shell_payload(head.strip(), field="head")
    if not raw:
        raise GitHubSecurityError("head is required")
    if raw.startswith("--"):
        raise GitHubSecurityError("head must not be a CLI flag (no --head spoof)")
    # owner:branch form (GitHub API head for same- or fork-repo PRs)
    if ":" in raw:
        head_owner, branch = raw.split(":", 1)
        if head_owner.lower() != owner.lower():
            raise GitHubSecurityError(
                f"head spoof denied: cross-owner head {raw!r} (owned={owner}/{repo})"
            )
        if not branch.strip():
            raise GitHubSecurityError(f"invalid head branch: {raw!r}")
        assert_no_shell_payload(branch, field="head.branch")
        return raw
    # Plain branch names may include slashes (feat/m2-...).
    # Reject owner/repo/branch triples that look like path spoofs.
    parts = raw.split("/")
    if len(parts) >= 3 and parts[0].lower() != owner.lower():
        raise GitHubSecurityError(f"head spoof denied: unexpected head form {raw!r}")
    assert_no_shell_payload(raw, field="head.branch")
    return raw


def assert_owned_repo(owner: str, repo: str, expected_owner: str, expected_repo: str) -> None:
    if owner.lower() != expected_owner.lower() or repo.lower() != expected_repo.lower():
        raise GitHubSecurityError(
            f"repo scope denied: {owner}/{repo} (allowed {expected_owner}/{expected_repo})"
        )


def reject_shell_command_form(command: str | None) -> None:
    """Explicitly reject any attempt to pass a raw `gh` / shell command string."""
    if command is None:
        return
    lowered = command.strip().lower()
    if lowered.startswith("gh ") or "gh pr create" in lowered or "&&" in command or ";" in command:
        raise GitHubSecurityError(
            "shell / gh string concat is denied; use structured create_pull_request arguments"
        )
