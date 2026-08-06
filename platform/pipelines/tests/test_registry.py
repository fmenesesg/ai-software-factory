"""Optional Quay publish path tests (task 7.2)."""

from __future__ import annotations

from asf_pipelines.registry import plan_registry_publish


def test_ghcr_primary_by_default() -> None:
    plan = plan_registry_publish(image_name="ai-software-factory-sample-app")
    assert plan.primary == "ghcr"
    assert plan.optional_quay is False
    assert plan.image_ref.startswith("ghcr.io/")
    assert plan.quay_ref is None


def test_quay_optional_when_full() -> None:
    plan = plan_registry_publish(
        image_name="ai-software-factory-sample-app",
        quay_org="example-org",
        enable_quay=True,
        profile="full",
    )
    assert plan.optional_quay is True
    assert plan.quay_ref == "quay.io/example-org/ai-software-factory-sample-app"
    assert plan.image_ref.startswith("ghcr.io/")
