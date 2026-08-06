"""Artifact ID contract for orchestrator handoffs (design Interfaces / Contracts)."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ValidationInfo, field_validator

# Stable keys persisted in LangGraph / orchestrator state.
ARTIFACT_ID_KEYS: tuple[str, ...] = (
    "issue_url",
    "pm_notes_url",
    "design_path",
    "architect_approval_id",
    "pr_url",
    "review_id",
    "image_digest",
    "ephemeral_url",
    "ns_name",
    "gitops_pr_url",
    "promote_approval_id",
    "sync_evidence",
)

_URL_RE = re.compile(r"^https?://[^\s]+$", re.IGNORECASE)
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_NS_RE = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")
_PATH_RE = re.compile(r"^(?!/)(?!.*\.\.)[A-Za-z0-9._/-]+$")
_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,256}$")


class ArtifactValidationError(ValueError):
    """Raised when an artifact ID value fails schema checks."""


def validate_artifact_id(key: str, value: str | None) -> str | None:
    """Validate a single artifact field. Empty/None is allowed (unset)."""
    if key not in ARTIFACT_ID_KEYS:
        raise ArtifactValidationError(f"unknown artifact key: {key}")
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ArtifactValidationError(f"{key} must be a string")

    if key in {"issue_url", "pm_notes_url", "pr_url", "ephemeral_url", "gitops_pr_url"}:
        if not _URL_RE.match(value):
            raise ArtifactValidationError(f"{key} must be an http(s) URL")
    elif key == "design_path":
        if not _PATH_RE.match(value):
            raise ArtifactValidationError(f"{key} must be a relative repo path without '..'")
    elif key == "image_digest":
        if not _DIGEST_RE.match(value):
            raise ArtifactValidationError(f"{key} must be sha256:<64 hex>")
    elif key == "ns_name":
        if not _NS_RE.match(value) or len(value) > 63:
            raise ArtifactValidationError(f"{key} must be a valid DNS-1123 label")
    else:
        if not _ID_RE.match(value):
            raise ArtifactValidationError(f"{key} has invalid identifier form")
    return value


class ArtifactIds(BaseModel):
    """Typed bundle of pipeline artifact references."""

    issue_url: str | None = None
    pm_notes_url: str | None = None
    design_path: str | None = None
    architect_approval_id: str | None = None
    pr_url: str | None = None
    review_id: str | None = None
    image_digest: str | None = None
    ephemeral_url: str | None = None
    ns_name: str | None = None
    gitops_pr_url: str | None = None
    promote_approval_id: str | None = None
    sync_evidence: str | None = None

    @field_validator("*", mode="before")
    @classmethod
    def _validate_fields(cls, value: Any, info: ValidationInfo) -> Any:
        key = info.field_name
        if key is None:
            return value
        return validate_artifact_id(key, value)


def validate_artifact_ids(payload: dict[str, Any]) -> ArtifactIds:
    """Validate a dict of artifact IDs; reject unknown keys."""
    unknown = set(payload) - set(ARTIFACT_ID_KEYS)
    if unknown:
        raise ArtifactValidationError(f"unknown artifact keys: {sorted(unknown)}")
    return ArtifactIds(**{k: payload.get(k) for k in ARTIFACT_ID_KEYS})
