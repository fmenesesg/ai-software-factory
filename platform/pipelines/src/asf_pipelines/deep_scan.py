"""Deep scan / RHACS-TAS policy hooks behind PROFILE=full (tasks 4.5, 7.1).

ACM is intentionally NOT referenced — multi-cluster is out of scope.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from asf_pipelines.scan_hooks import build_scan_check_stub


def resolve_profile(raw: str | None = None) -> str:
    value = (raw or os.environ.get("PROFILE") or "standard").strip().lower()
    if value not in {"minimal", "standard", "full"}:
        raise ValueError(f"unsupported PROFILE={value!r}; expected minimal|standard|full")
    return value


@dataclass(frozen=True, slots=True)
class DeepScanPlan:
    profile: str
    enabled: bool
    engines: tuple[str, ...]
    check_name: str
    summary: str


def plan_deep_scan(*, profile: str | None = None) -> DeepScanPlan:
    """Gate deep RHACS/TAS-style scans on PROFILE=full only."""
    resolved = resolve_profile(profile)
    if resolved != "full":
        return DeepScanPlan(
            profile=resolved,
            enabled=False,
            engines=(),
            check_name="asf/deep-scan",
            summary=f"Deep scan skipped (PROFILE={resolved}; enable with PROFILE=full)",
        )
    return DeepScanPlan(
        profile=resolved,
        enabled=True,
        engines=("rhacs", "tas"),
        check_name="asf/deep-scan",
        summary="Deep scan policy hooks (RHACS + TAS) — PROFILE=full; ACM not used",
    )


def build_deep_scan_check(
    *,
    profile: str | None = None,
    head_sha: str = "0" * 40,
    image_digest: str | None = None,
    pr_url: str | None = None,
) -> dict[str, Any]:
    """Build GitHub Check payload for deep scan (or skipped stub)."""
    plan = plan_deep_scan(profile=profile)
    conclusion = "neutral" if not plan.enabled else "success"
    details: dict[str, Any] = {
        "profile": plan.profile,
        "enabled": plan.enabled,
        "engines": ",".join(plan.engines) if plan.engines else "none",
        "acm": False,
    }
    if image_digest:
        details["image_digest"] = image_digest
    if pr_url:
        details["pr_url"] = pr_url
    return build_scan_check_stub(
        check_name=plan.check_name,
        title="Deep scan (RHACS/TAS)" if plan.enabled else "Deep scan skipped",
        summary=plan.summary,
        conclusion=conclusion,
        head_sha=head_sha,
        details=details,
    )
