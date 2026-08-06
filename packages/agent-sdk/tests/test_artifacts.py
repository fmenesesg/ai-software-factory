"""Unit tests for artifact ID validators (task 1.3)."""

import pytest

from agent_sdk.artifacts import (
    ArtifactIds,
    ArtifactValidationError,
    validate_artifact_id,
    validate_artifact_ids,
)


def test_validate_issue_url_ok() -> None:
    assert (
        validate_artifact_id("issue_url", "https://github.com/fmenesesg/ai-software-factory/issues/1")
        is not None
    )


def test_validate_issue_url_rejects_non_url() -> None:
    with pytest.raises(ArtifactValidationError):
        validate_artifact_id("issue_url", "not-a-url")


def test_validate_design_path_rejects_traversal() -> None:
    with pytest.raises(ArtifactValidationError):
        validate_artifact_id("design_path", "../etc/passwd")


def test_validate_image_digest() -> None:
    digest = "sha256:" + ("a" * 64)
    assert validate_artifact_id("image_digest", digest) == digest
    with pytest.raises(ArtifactValidationError):
        validate_artifact_id("image_digest", "sha256:deadbeef")


def test_validate_ns_name() -> None:
    assert validate_artifact_id("ns_name", "asf-workshop-demo") == "asf-workshop-demo"
    with pytest.raises(ArtifactValidationError):
        validate_artifact_id("ns_name", "ASF_BAD")


def test_unknown_key_rejected() -> None:
    with pytest.raises(ArtifactValidationError):
        validate_artifact_id("secret_token", "x")


def test_validate_artifact_ids_bundle() -> None:
    ids = validate_artifact_ids(
        {
            "issue_url": "https://github.com/o/r/issues/1",
            "design_path": "docs/architecture/adr/001-monorepo.md",
            "ns_name": "asf-workshop-1",
        }
    )
    assert isinstance(ids, ArtifactIds)
    assert ids.issue_url.endswith("/issues/1")


def test_validate_artifact_ids_rejects_unknown() -> None:
    with pytest.raises(ArtifactValidationError):
        validate_artifact_ids({"issue_url": "https://example.com/i/1", "extra": "nope"})


def test_empty_values_allowed() -> None:
    assert validate_artifact_id("pr_url", None) is None
    assert validate_artifact_id("pr_url", "") is None
