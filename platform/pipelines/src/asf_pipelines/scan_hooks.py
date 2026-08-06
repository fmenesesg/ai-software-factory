"""PR Check stubs for Security/QA scan hooks (MVP placeholders — visible on PR)."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from typing import Any, Protocol


class GitHubHttp(Protocol):
    def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...


@dataclass(frozen=True)
class ScanHookEvidence:
    check_name: str
    check_payload: dict[str, Any]
    pr_number: int
    dry_run: bool
    published: bool

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)


def build_scan_check_stub(
    *,
    check_name: str,
    title: str,
    summary: str,
    conclusion: str = "neutral",
    head_sha: str = "0000000000000000000000000000000000000000",
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a GitHub Check Runs payload (placeholder scan/test hook)."""
    detail_lines = []
    for key, value in (details or {}).items():
        detail_lines.append(f"{key}={value}")
    text = "\n".join(detail_lines) if detail_lines else "MVP placeholder — deep policy deferred."
    return {
        "name": check_name,
        "head_sha": head_sha,
        "status": "completed",
        "conclusion": conclusion,
        "output": {
            "title": title,
            "summary": summary,
            "text": text,
        },
    }


def publish_scan_hooks(
    *,
    owner: str,
    repo: str,
    pr_number: int,
    head_sha: str = "0000000000000000000000000000000000000000",
    dry_run: bool = False,
    token: str | None = None,
    http: GitHubHttp | None = None,
    include_security: bool = True,
    include_qa: bool = True,
) -> list[ScanHookEvidence]:
    """Publish placeholder Security/QA Checks so they are visible on the PR."""
    if pr_number < 0:
        raise ValueError("pr_number must be >= 0")

    stubs: list[dict[str, Any]] = []
    if include_security:
        stubs.append(
            build_scan_check_stub(
                check_name="asf/security-scan",
                title="Security scan placeholder",
                summary="MVP stub — deep scan deferred (task 4.5)",
                conclusion="neutral",
                head_sha=head_sha,
                details={"stub": True, "agent": "security"},
            )
        )
    if include_qa:
        stubs.append(
            build_scan_check_stub(
                check_name="asf/qa-tests",
                title="QA test placeholder",
                summary="MVP stub — full suites deferred (M6)",
                conclusion="neutral",
                head_sha=head_sha,
                details={"stub": True, "agent": "qa"},
            )
        )

    if dry_run:
        return [
            ScanHookEvidence(
                check_name=str(payload["name"]),
                check_payload=payload,
                pr_number=pr_number,
                dry_run=True,
                published=False,
            )
            for payload in stubs
        ]

    client = http
    if client is None:
        from asf_pipelines.pr_evidence import LiveGitHubHttp

        if not token:
            raise ValueError("GITHUB_TOKEN required when dry_run is false")
        client = LiveGitHubHttp(token=token)

    results: list[ScanHookEvidence] = []
    for payload in stubs:
        client.request(
            "POST",
            f"/repos/{owner}/{repo}/check-runs",
            json=payload,
        )
        results.append(
            ScanHookEvidence(
                check_name=str(payload["name"]),
                check_payload=payload,
                pr_number=pr_number,
                dry_run=False,
                published=True,
            )
        )
    return results


def main() -> None:
    dry_run = os.environ.get("ASF_DRY_RUN", "false").lower() in {"1", "true", "yes"}
    evidence = publish_scan_hooks(
        owner=os.environ["ASF_GITHUB_OWNER"],
        repo=os.environ["ASF_GITHUB_REPO"],
        pr_number=int(os.environ["ASF_PR_NUMBER"]),
        head_sha=os.environ.get("ASF_HEAD_SHA", "0" * 40),
        dry_run=dry_run,
        token=os.environ.get("GITHUB_TOKEN"),
    )
    print(json.dumps([json.loads(e.to_json()) for e in evidence], indent=2))


if __name__ == "__main__":
    main()
