"""Desired-state helpers for monorepo platform/gitops/."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
DESIRED_DIR = ROOT / "desired"
ARGO_DIR = ROOT / "argo"


def desired_state_dir() -> Path:
    return DESIRED_DIR


def argo_stub_path() -> Path:
    return ARGO_DIR / "application-stub.yaml"


def load_desired_state_summary() -> dict[str, Any]:
    """Summarize desired-state manifests used for promote PRs."""
    manifests: list[dict[str, Any]] = []
    for path in sorted(DESIRED_DIR.glob("*.yaml")):
        for data in yaml.safe_load_all(path.read_text(encoding="utf-8")):
            if not isinstance(data, dict):
                continue
            manifests.append(
                {
                    "file": path.name,
                    "kind": data.get("kind"),
                    "name": (data.get("metadata") or {}).get("name"),
                    "image": _extract_image(data),
                }
            )
    argo: dict[str, Any] | None = None
    if argo_stub_path().is_file():
        argo_data = yaml.safe_load(argo_stub_path().read_text(encoding="utf-8"))
        if isinstance(argo_data, dict):
            argo = {
                "file": argo_stub_path().name,
                "kind": argo_data.get("kind"),
                "name": (argo_data.get("metadata") or {}).get("name"),
            }
    return {
        "root": "platform/gitops/desired",
        "manifests": manifests,
        "argo_stub": argo,
    }


def _extract_image(manifest: dict[str, Any]) -> str | None:
    spec = manifest.get("spec") or {}
    template = (spec.get("template") or {}).get("spec") or {}
    containers = template.get("containers") or spec.get("containers") or []
    if containers and isinstance(containers[0], dict):
        return containers[0].get("image")
    if "image" in spec:
        return str(spec.get("image"))
    return None


def render_desired_image_pin(*, image: str, digest: str) -> str:
    """Return a desired-state image pin line for promote PR body/diff narrative."""
    if not digest.startswith("sha256:"):
        raise ValueError("digest must be sha256:...")
    return f"{image}@{digest}"
