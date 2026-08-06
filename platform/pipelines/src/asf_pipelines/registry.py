"""Optional Quay publish path — GHCR remains MVP primary (task 7.2)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RegistryPublishPlan:
    primary: str
    optional_quay: bool
    image_ref: str
    quay_ref: str | None
    notes: str


def plan_registry_publish(
    *,
    image_name: str,
    ghcr_owner: str = "fmenesesg",
    quay_org: str | None = None,
    enable_quay: bool = False,
    profile: str = "standard",
) -> RegistryPublishPlan:
    """
    Resolve publish targets.

    GHCR is always primary for MVP. Quay is optional and recommended only when
    PROFILE=full and enable_quay is true.
    """
    primary = f"ghcr.io/{ghcr_owner}/{image_name}"
    if enable_quay and profile == "full" and quay_org:
        quay = f"quay.io/{quay_org}/{image_name}"
        return RegistryPublishPlan(
            primary="ghcr",
            optional_quay=True,
            image_ref=primary,
            quay_ref=quay,
            notes="GHCR primary; Quay optional mirror under PROFILE=full",
        )
    return RegistryPublishPlan(
        primary="ghcr",
        optional_quay=False,
        image_ref=primary,
        quay_ref=None,
        notes="GHCR MVP primary — Quay disabled (set PROFILE=full + enable_quay)",
    )
