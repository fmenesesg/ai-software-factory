"""GitHub HITL poller — Architect approval gate (poll-only for workshop)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class HitlPoller(Protocol):
    def poll_architect_approval(
        self,
        *,
        owner: str,
        repo: str,
        pull_number: int | None = None,
        reviews: list[dict[str, Any]] | None = None,
    ) -> str | None:
        """Return approval_id when a required APPROVED review exists; else None."""


@dataclass
class StaticHitlPoller:
    """Test/demo poller returning a fixed approval id (or None)."""

    approval_id: str | None = None

    def poll_architect_approval(
        self,
        *,
        owner: str,
        repo: str,
        pull_number: int | None = None,
        reviews: list[dict[str, Any]] | None = None,
    ) -> str | None:
        return self.approval_id


@dataclass
class GitHubReviewPoller:
    """Extract Architect approval_id from GitHub PR review payloads."""

    required_state: str = "APPROVED"
    calls: list[dict[str, Any]] = field(default_factory=list)

    def poll_architect_approval(
        self,
        *,
        owner: str,
        repo: str,
        pull_number: int | None = None,
        reviews: list[dict[str, Any]] | None = None,
    ) -> str | None:
        self.calls.append(
            {"owner": owner, "repo": repo, "pull_number": pull_number, "reviews": reviews or []}
        )
        for review in reviews or []:
            state = str(review.get("state") or "").upper()
            if state == self.required_state:
                review_id = review.get("id") or review.get("node_id")
                if review_id is not None:
                    return str(review_id)
        return None
