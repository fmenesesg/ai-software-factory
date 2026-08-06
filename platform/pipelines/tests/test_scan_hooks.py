"""Scan hook placeholder Check tests (task 4.4)."""

from __future__ import annotations

from asf_pipelines.pr_evidence import InMemoryGitHubHttp
from asf_pipelines.scan_hooks import build_scan_check_stub, publish_scan_hooks


def test_build_scan_check_stub_visible_name() -> None:
    payload = build_scan_check_stub(
        check_name="asf/security-scan",
        title="Security scan placeholder",
        summary="stub",
    )
    assert payload["name"] == "asf/security-scan"
    assert payload["status"] == "completed"
    assert payload["conclusion"] == "neutral"


def test_publish_scan_hooks_dry_run() -> None:
    http = InMemoryGitHubHttp()
    results = publish_scan_hooks(
        owner="fmenesesg",
        repo="ai-software-factory",
        pr_number=11,
        dry_run=True,
        http=http,
    )
    assert len(results) == 2
    names = {r.check_name for r in results}
    assert names == {"asf/security-scan", "asf/qa-tests"}
    assert all(r.dry_run and not r.published for r in results)
    assert http.calls == []


def test_publish_scan_hooks_posts_check_runs() -> None:
    http = InMemoryGitHubHttp()
    results = publish_scan_hooks(
        owner="fmenesesg",
        repo="ai-software-factory",
        pr_number=11,
        dry_run=False,
        http=http,
        head_sha="deadbeef",
    )
    assert all(r.published for r in results)
    assert len(http.calls) == 2
    assert all(c["path"].endswith("/check-runs") for c in http.calls)
    assert http.calls[0]["json"]["name"] == "asf/security-scan"
    assert http.calls[1]["json"]["name"] == "asf/qa-tests"
