"""PR ephemeral evidence helpers (URL + namespace comment and Check stub)."""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from typing import Any, Protocol

_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class GitHubHttp(Protocol):
    def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...


@dataclass(frozen=True)
class EphemeralEvidence:
    ephemeral_url: str
    ns_name: str
    image_digest: str
    pr_number: int
    comment_body: str
    check_name: str
    check_payload: dict[str, Any]
    dry_run: bool
    commented: bool
    check_stubbed: bool

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)


@dataclass
class InMemoryGitHubHttp:
    calls: list[dict[str, Any]]

    def __init__(self) -> None:
        self.calls = []

    def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.calls.append({"method": method, "path": path, "json": json})
        if method.upper() == "POST" and path.endswith("/comments"):
            return {"id": 1, "html_url": "https://github.com/example/comment/1"}
        if method.upper() == "POST" and path.endswith("/check-runs"):
            return {"id": 99, "html_url": "https://github.com/example/check/99"}
        return {"ok": True}


@dataclass
class LiveGitHubHttp:
    token: str
    api_base: str = "https://api.github.com"

    def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        import httpx

        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        with httpx.Client(timeout=30.0, headers=headers) as client:
            response = client.request(method, self.api_base.rstrip("/") + path, json=json)
            response.raise_for_status()
            if not response.content:
                return {}
            data = response.json()
            return data if isinstance(data, dict) else {"_list": data}


def format_ephemeral_comment(*, ephemeral_url: str, namespace: str, image_digest: str) -> str:
    return (
        "## Ephemeral environment\n\n"
        f"- **URL:** {ephemeral_url}\n"
        f"- **Namespace:** `{namespace}`\n"
        f"- **Image digest:** `{image_digest}`\n"
    )


def build_check_stub(
    *,
    ephemeral_url: str,
    namespace: str,
    image_digest: str,
    head_sha: str = "0000000000000000000000000000000000000000",
) -> dict[str, Any]:
    return {
        "name": "asf/ephemeral",
        "head_sha": head_sha,
        "status": "completed",
        "conclusion": "success",
        "output": {
            "title": "Ephemeral deploy ready",
            "summary": f"Namespace `{namespace}` · {ephemeral_url}",
            "text": f"image_digest={image_digest}\nns_name={namespace}\nephemeral_url={ephemeral_url}\n",
        },
    }


def publish_ephemeral_evidence(
    *,
    owner: str,
    repo: str,
    pr_number: int,
    ephemeral_url: str,
    namespace: str,
    image_digest: str,
    dry_run: bool = False,
    token: str | None = None,
    http: GitHubHttp | None = None,
    head_sha: str = "0000000000000000000000000000000000000000",
) -> EphemeralEvidence:
    if not ephemeral_url.startswith("http"):
        raise ValueError("ephemeral_url must be an http(s) URL")
    if not _DIGEST_RE.match(image_digest):
        raise ValueError("image_digest must be sha256:<64 hex>")
    if pr_number < 0:
        raise ValueError("pr_number must be >= 0")

    comment_body = format_ephemeral_comment(
        ephemeral_url=ephemeral_url,
        namespace=namespace,
        image_digest=image_digest,
    )
    check_payload = build_check_stub(
        ephemeral_url=ephemeral_url,
        namespace=namespace,
        image_digest=image_digest,
        head_sha=head_sha,
    )

    commented = False
    check_stubbed = False
    if dry_run:
        return EphemeralEvidence(
            ephemeral_url=ephemeral_url,
            ns_name=namespace,
            image_digest=image_digest,
            pr_number=pr_number,
            comment_body=comment_body,
            check_name="asf/ephemeral",
            check_payload=check_payload,
            dry_run=True,
            commented=False,
            check_stubbed=False,
        )

    client = http
    if client is None:
        if not token:
            raise ValueError("GITHUB_TOKEN required when dry_run is false")
        client = LiveGitHubHttp(token=token)

    client.request(
        "POST",
        f"/repos/{owner}/{repo}/issues/{pr_number}/comments",
        json={"body": comment_body},
    )
    commented = True
    client.request(
        "POST",
        f"/repos/{owner}/{repo}/check-runs",
        json=check_payload,
    )
    check_stubbed = True
    return EphemeralEvidence(
        ephemeral_url=ephemeral_url,
        ns_name=namespace,
        image_digest=image_digest,
        pr_number=pr_number,
        comment_body=comment_body,
        check_name="asf/ephemeral",
        check_payload=check_payload,
        dry_run=False,
        commented=commented,
        check_stubbed=check_stubbed,
    )


def main() -> None:
    dry_run = os.environ.get("ASF_DRY_RUN", "false").lower() in {"1", "true", "yes"}
    evidence = publish_ephemeral_evidence(
        owner=os.environ["ASF_GITHUB_OWNER"],
        repo=os.environ["ASF_GITHUB_REPO"],
        pr_number=int(os.environ["ASF_PR_NUMBER"]),
        ephemeral_url=os.environ["ASF_EPHEMERAL_URL"],
        namespace=os.environ["ASF_NAMESPACE"],
        image_digest=os.environ["ASF_IMAGE_DIGEST"],
        dry_run=dry_run,
        token=os.environ.get("GITHUB_TOKEN"),
    )
    path = os.environ.get("ASF_EVIDENCE_PATH")
    payload = evidence.to_json()
    if path:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(payload)
    print(payload)


if __name__ == "__main__":
    main()
