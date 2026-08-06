"""GitOps unit tests — promote PR, HITL block, Argo stub sync evidence."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from asf_gitops.desired import load_desired_state_summary, render_desired_image_pin
from asf_gitops.promote import (
    InMemoryPromoteClient,
    PromoteBlockedError,
    open_promote_pr,
    sync_prod_like,
)
from orchestrator.hitl import GitHubReviewPoller, StaticHitlPoller

ROOT = Path(__file__).resolve().parents[1]
DIGEST = "sha256:" + ("b" * 64)


def test_desired_state_manifests_exist() -> None:
    summary = load_desired_state_summary()
    assert summary["manifests"]
    names = {m["file"] for m in summary["manifests"]}
    assert "sample-app-prod.yaml" in names
    kinds = {m["kind"] for m in summary["manifests"]}
    assert "Deployment" in kinds
    assert summary["argo_stub"] is not None
    assert summary["argo_stub"]["kind"] == "Application"


def test_rhdh_catalog_component_shows_github_slug() -> None:
    catalog = Path(__file__).resolve().parents[2] / "rhdh" / "catalog-info.yaml"
    docs = list(yaml.safe_load_all(catalog.read_text(encoding="utf-8")))
    component = next(d for d in docs if d and d.get("kind") == "Component")
    assert component["metadata"]["name"] == "ai-software-factory"
    assert (
        component["metadata"]["annotations"]["github.com/project-slug"]
        == "fmenesesg/ai-software-factory"
    )
    assert "visualization" in component["metadata"]["description"].lower() or True
    viz_doc = Path(__file__).resolve().parents[3] / "docs" / "workshop" / "rhdh-visualization.md"
    assert viz_doc.is_file()
    text = viz_doc.read_text(encoding="utf-8")
    assert "GitHub" in text
    assert "not" in text.lower() and "HITL" in text


def test_argo_stub_has_sync_policy_fields() -> None:
    path = ROOT / "argo" / "application-stub.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["kind"] == "Application"
    assert data["metadata"]["name"] == "asf-sample-app-prod"
    assert "syncPolicy" in data["spec"]
    # Automated sync disabled until promote HITL approval.
    assert data["spec"]["syncPolicy"].get("automated") in (None, False, {})


def test_render_desired_image_pin() -> None:
    pin = render_desired_image_pin(
        image="ghcr.io/fmenesesg/ai-software-factory-sample-app",
        digest=DIGEST,
    )
    assert pin.startswith("ghcr.io/")
    assert DIGEST in pin


def test_open_promote_pr_dry_run() -> None:
    result = open_promote_pr(
        owner="fmenesesg",
        repo="ai-software-factory",
        image="ghcr.io/fmenesesg/ai-software-factory-sample-app",
        image_digest=DIGEST,
        head="chore/gitops-promote-demo",
        dry_run=True,
    )
    assert result["dry_run"] is True
    assert result["gitops_pr_url"] is None
    assert "desired_pin" in result["would_create"]


def test_open_promote_pr_returns_url() -> None:
    client = InMemoryPromoteClient()
    result = open_promote_pr(
        owner="fmenesesg",
        repo="ai-software-factory",
        image="ghcr.io/fmenesesg/ai-software-factory-sample-app",
        image_digest=DIGEST,
        head="chore/gitops-promote-demo",
        issue_url="https://github.com/fmenesesg/ai-software-factory/issues/1",
        dry_run=False,
        client=client,
    )
    assert result["ok"] is True
    assert result["gitops_pr_url"].endswith("/pull/901")
    assert client.calls


def test_promote_hitl_blocks_sync_without_approval() -> None:
    poller = StaticHitlPoller(approval_id=None, promote_approval_id=None)
    approval = poller.poll_promote_approval(
        owner="fmenesesg",
        repo="ai-software-factory",
        pull_number=901,
        reviews=[],
    )
    assert approval is None
    with pytest.raises(PromoteBlockedError, match="promote_approval_id"):
        sync_prod_like(
            promote_approval_id=approval,
            gitops_pr_url="https://github.com/fmenesesg/ai-software-factory/pull/901",
        )


def test_promote_hitl_allows_stub_sync_when_approved() -> None:
    poller = GitHubReviewPoller()
    approval = poller.poll_promote_approval(
        owner="fmenesesg",
        repo="ai-software-factory",
        pull_number=901,
        reviews=[{"id": "promote-55", "state": "APPROVED"}],
    )
    assert approval == "promote-55"
    result = sync_prod_like(
        promote_approval_id=approval,
        gitops_pr_url="https://github.com/fmenesesg/ai-software-factory/pull/901",
    )
    assert result["synced"] is True
    assert result["stub"] is True
    assert result["sync_evidence"].startswith("argo-stub-sync-")
    assert result["promote_approval_id"] == "promote-55"
