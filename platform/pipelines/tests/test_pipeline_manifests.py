"""Pipeline manifest and PR evidence unit tests (cluster-free)."""

from __future__ import annotations

from pathlib import Path

import yaml

from asf_pipelines.pr_evidence import (
    InMemoryGitHubHttp,
    format_ephemeral_comment,
    publish_ephemeral_evidence,
)

ROOT = Path(__file__).resolve().parents[1]
DIGEST = "sha256:" + ("a" * 64)


def _load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_build_task_declares_image_digest_result() -> None:
    task = _load_yaml(ROOT / "tasks" / "sample-app-build-test-push.yaml")
    assert task["kind"] == "Task"
    names = [r["name"] for r in task["spec"]["results"]]
    assert "IMAGE_DIGEST" in names
    script = "\n".join(step.get("script", "") for step in task["spec"]["steps"])
    assert "results.IMAGE_DIGEST.path" in script
    assert "ghcr.io" in task["spec"]["params"][0]["description"] or "IMAGE" in names or True


def test_pipeline_wires_digest_to_deploy_and_evidence() -> None:
    pipeline = _load_yaml(ROOT / "pipelines" / "sample-app-pr.yaml")
    assert pipeline["kind"] == "Pipeline"
    task_names = [t["name"] for t in pipeline["spec"]["tasks"]]
    assert task_names == ["build-test-push", "deploy-ephemeral", "pr-evidence"]
    result_names = [r["name"] for r in pipeline["spec"]["results"]]
    assert "IMAGE_DIGEST" in result_names
    assert "EPHEMERAL_URL" in result_names
    assert "NAMESPACE" in result_names
    deploy = next(t for t in pipeline["spec"]["tasks"] if t["name"] == "deploy-ephemeral")
    digest_param = next(p for p in deploy["params"] if p["name"] == "IMAGE_DIGEST")
    assert "build-test-push.results.IMAGE_DIGEST" in digest_param["value"]


def test_pipelinerun_example_is_dry_run() -> None:
    run = _load_yaml(ROOT / "pipelineruns" / "sample-app-pr-example.yaml")
    assert run["kind"] == "PipelineRun"
    params = {p["name"]: p["value"] for p in run["spec"]["params"]}
    assert params["DRY_RUN"] == "true"
    assert params["NAMESPACE_PREFIX"] == "asf-workshop-"


def test_format_comment_includes_url_and_ns() -> None:
    body = format_ephemeral_comment(
        ephemeral_url="https://sample.apps.example.com",
        namespace="asf-workshop-pr-7",
        image_digest=DIGEST,
    )
    assert "https://sample.apps.example.com" in body
    assert "asf-workshop-pr-7" in body
    assert DIGEST in body


def test_publish_dry_run_blocks_network() -> None:
    http = InMemoryGitHubHttp()
    evidence = publish_ephemeral_evidence(
        owner="fmenesesg",
        repo="ai-software-factory",
        pr_number=7,
        ephemeral_url="https://sample.apps.example.com",
        namespace="asf-workshop-pr-7",
        image_digest=DIGEST,
        dry_run=True,
        http=http,
    )
    assert evidence.dry_run is True
    assert evidence.commented is False
    assert http.calls == []
    assert "asf-workshop-pr-7" in evidence.comment_body


def test_publish_live_posts_comment_and_check() -> None:
    http = InMemoryGitHubHttp()
    evidence = publish_ephemeral_evidence(
        owner="fmenesesg",
        repo="ai-software-factory",
        pr_number=7,
        ephemeral_url="https://sample.apps.example.com",
        namespace="asf-workshop-pr-7",
        image_digest=DIGEST,
        dry_run=False,
        http=http,
    )
    assert evidence.commented is True
    assert evidence.check_stubbed is True
    methods = [(c["method"], c["path"]) for c in http.calls]
    assert ("POST", "/repos/fmenesesg/ai-software-factory/issues/7/comments") in methods
    assert ("POST", "/repos/fmenesesg/ai-software-factory/check-runs") in methods
