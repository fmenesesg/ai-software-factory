"""GitHub HITL poller — Architect + promote approval gates (poll-only for workshop)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


def _first_approved_id(
    reviews: list[dict[str, Any]] | None,
    *,
    required_state: str = "APPROVED",
) -> str | None:
    for review in reviews or []:
        state = str(review.get("state") or "").upper()
        if state == required_state:
            review_id = review.get("id") or review.get("node_id")
            if review_id is not None:
                return str(review_id)
    return None


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

    def poll_promote_approval(
        self,
        *,
        owner: str,
        repo: str,
        pull_number: int | None = None,
        reviews: list[dict[str, Any]] | None = None,
    ) -> str | None:
        """Return promote_approval_id when GitOps PR is approved; else None."""


@dataclass
class StaticHitlPoller:
    """Test/demo poller returning fixed Architect / promote approval ids."""

    approval_id: str | None = None
    promote_approval_id: str | None = None

    def poll_architect_approval(
        self,
        *,
        owner: str,
        repo: str,
        pull_number: int | None = None,
        reviews: list[dict[str, Any]] | None = None,
    ) -> str | None:
        return self.approval_id

    def poll_promote_approval(
        self,
        *,
        owner: str,
        repo: str,
        pull_number: int | None = None,
        reviews: list[dict[str, Any]] | None = None,
    ) -> str | None:
        return self.promote_approval_id


@dataclass
class GitHubReviewPoller:
    """Extract approval ids from GitHub PR review payloads (Architect or promote)."""

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
            {
                "kind": "architect",
                "owner": owner,
                "repo": repo,
                "pull_number": pull_number,
                "reviews": reviews or [],
            }
        )
        return _first_approved_id(reviews, required_state=self.required_state)

    def poll_promote_approval(
        self,
        *,
        owner: str,
        repo: str,
        pull_number: int | None = None,
        reviews: list[dict[str, Any]] | None = None,
    ) -> str | None:
        self.calls.append(
            {
                "kind": "promote",
                "owner": owner,
                "repo": repo,
                "pull_number": pull_number,
                "reviews": reviews or [],
            }
        )
        return _first_approved_id(reviews, required_state=self.required_state)
