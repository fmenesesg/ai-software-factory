"""Deep scan profile gating tests (tasks 4.5 / 7.1)."""

from __future__ import annotations

import pytest

from asf_pipelines.deep_scan import build_deep_scan_check, plan_deep_scan, resolve_profile


def test_resolve_profile_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        resolve_profile("enterprise")


def test_deep_scan_disabled_on_standard() -> None:
    plan = plan_deep_scan(profile="standard")
    assert plan.enabled is False
    assert plan.engines == ()
    check = build_deep_scan_check(profile="standard")
    assert check["name"] == "asf/deep-scan"
    assert "skipped" in check["output"]["summary"].lower()
    assert "acm=False" in check["output"]["text"]


def test_deep_scan_enabled_on_full() -> None:
    plan = plan_deep_scan(profile="full")
    assert plan.enabled is True
    assert "rhacs" in plan.engines
    assert "tas" in plan.engines
    check = build_deep_scan_check(profile="full", image_digest="sha256:dead")
    assert check["conclusion"] == "success"
    assert "RHACS" in check["output"]["summary"]
    assert "ACM" in check["output"]["summary"] or "acm=False" in check["output"]["text"]
