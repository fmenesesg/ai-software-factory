"""Promote PR flow + HITL-gated prod-like Argo stub sync."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol
from uuid import uuid4

from asf_gitops.desired import load_desired_state_summary, render_desired_image_pin


class PromoteBlockedError(RuntimeError):
    """Raised when prod-like sync is attempted without GitHub promote approval."""


class GitHubPromoteClient(Protocol):
    def create_pull_request(self, payload: dict[str, Any]) -> dict[str, Any]: ...


@dataclass
class InMemoryPromoteClient:
    calls: list[dict[str, Any]]

    def __init__(self) -> None:
        self.calls = []

    def create_pull_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(payload)
        number = 900 + len(self.calls)
        return {
            "number": number,
            "html_url": f"https://github.com/{payload['owner']}/{payload['repo']}/pull/{number}",
            "head": payload["head"],
            "base": payload["base"],
        }


def build_promote_pr_payload(
    *,
    owner: str,
    repo: str,
    image: str,
    image_digest: str,
    head: str,
    base: str = "main",
    issue_url: str | None = None,
) -> dict[str, Any]:
    pin = render_desired_image_pin(image=image, digest=image_digest)
    summary = load_desired_state_summary()
    body_lines = [
        "## GitOps promote",
        "",
        f"- Desired-state pin: `{pin}`",
        f"- Manifests: {', '.join(m['file'] for m in summary['manifests']) or '(none)'}",
        "",
        "Promotion requires GitHub approval before prod-like Argo sync (HITL).",
    ]
    if issue_url:
        body_lines.extend(["", f"Related: {issue_url}"])
    return {
        "owner": owner,
        "repo": repo,
        "title": f"chore(gitops): promote {image.split('/')[-1]}@{image_digest[:19]}",
        "body": "\n".join(body_lines),
        "head": head,
        "base": base,
        "desired_pin": pin,
    }


def open_promote_pr(
    *,
    owner: str,
    repo: str,
    image: str,
    image_digest: str,
    head: str,
    base: str = "main",
    issue_url: str | None = None,
    dry_run: bool = False,
    client: GitHubPromoteClient | None = None,
) -> dict[str, Any]:
    """Open (or dry-run) a GitOps promote PR in the monorepo."""
    payload = build_promote_pr_payload(
        owner=owner,
        repo=repo,
        image=image,
        image_digest=image_digest,
        head=head,
        base=base,
        issue_url=issue_url,
    )
    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "blocked": True,
            "reason": "dry_run",
            "gitops_pr_url": None,
            "would_create": payload,
        }
    gh = client or InMemoryPromoteClient()
    result = gh.create_pull_request(payload)
    return {
        "ok": True,
        "dry_run": False,
        "gitops_pr_url": result.get("html_url"),
        "number": result.get("number"),
        "desired_pin": payload["desired_pin"],
    }


def sync_prod_like(
    *,
    promote_approval_id: str | None,
    gitops_pr_url: str | None,
    application_name: str = "asf-sample-app-prod",
) -> dict[str, Any]:
    """Stub Argo sync — blocked without GitHub promote approval (HITL)."""
    if not promote_approval_id:
        raise PromoteBlockedError("prod-like sync blocked: promote_approval_id required (GitHub HITL)")
    if not gitops_pr_url:
        raise PromoteBlockedError("prod-like sync blocked: gitops_pr_url required")

    sync_evidence = f"argo-stub-sync-{uuid4().hex[:12]}"
    return {
        "ok": True,
        "synced": True,
        "application": application_name,
        "gitops_pr_url": gitops_pr_url,
        "promote_approval_id": promote_approval_id,
        "sync_evidence": sync_evidence,
        "stub": True,
        "message": "Argo Application stub sync recorded (no live cluster mutate)",
    }
