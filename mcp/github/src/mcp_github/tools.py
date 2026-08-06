"""GitHub MCP tools — structured REST calls only (injectable HTTP client)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from agent_sdk.otel import factory_span

from mcp_github.config import GitHubMcpSettings
from mcp_github.security import (
    GitHubSecurityError,
    assert_no_shell_payload,
    assert_owned_head_ref,
    assert_owned_repo,
    reject_shell_command_form,
)


class GitHubHttp(Protocol):
    def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...


class GitHubToolError(RuntimeError):
    pass


@dataclass
class InMemoryGitHubHttp:
    """Test double recording structured API calls (never shells out)."""

    calls: list[dict[str, Any]] = field(default_factory=list)
    responses: dict[str, dict[str, Any]] = field(default_factory=dict)

    def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.calls.append({"method": method, "path": path, "json": json})
        key = f"{method.upper()} {path}"
        if key in self.responses:
            return self.responses[key]
        if method.upper() == "POST" and path.endswith("/pulls"):
            return {
                "number": 42,
                "html_url": "https://github.com/example/repo/pull/42",
                "head": {"ref": (json or {}).get("head", "feat/x")},
                "base": {"ref": (json or {}).get("base", "main")},
            }
        if method.upper() == "GET" and "/pulls/" in path and path.endswith("/reviews"):
            return {"_list": []}  # tools unwrap list responses
        if method.upper() == "POST" and "/pulls/" in path and path.endswith("/reviews"):
            return {
                "id": 77,
                "state": (json or {}).get("event", "COMMENTED"),
                "html_url": "https://github.com/example/pull/1#pullrequestreview-77",
            }
        if method.upper() == "POST" and path.endswith("/issues") is False and "/comments" in path:
            return {"id": 1, "html_url": "https://github.com/example/comment/1"}
        return {"ok": True}


@dataclass
class LiveGitHubHttp:
    """Minimal httpx-backed GitHub API client (token from settings)."""

    settings: GitHubMcpSettings

    def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        import httpx

        if not self.settings.github_token:
            raise GitHubToolError("GITHUB_TOKEN is required for live GitHub MCP calls")
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.settings.github_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        url = self.settings.api_base.rstrip("/") + path
        with httpx.Client(timeout=30.0, headers=headers) as client:
            response = client.request(method, url, json=json)
            if response.status_code >= 400:
                raise GitHubToolError(f"GitHub API {response.status_code}: {response.text}")
            if response.status_code == 204 or not response.content:
                return {}
            data = response.json()
            if isinstance(data, list):
                return {"_list": data}
            if isinstance(data, dict):
                return data
            return {"value": data}


@dataclass
class GitHubTools:
    settings: GitHubMcpSettings
    http: GitHubHttp | None = None

    def __post_init__(self) -> None:
        if self.http is None:
            self.http = LiveGitHubHttp(self.settings)

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {"name": "create_pull_request", "description": "Open PR on owned repo", "mutating": True},
            {"name": "list_pull_reviews", "description": "List PR reviews for HITL poll", "mutating": False},
            {"name": "submit_pull_review", "description": "Submit APPROVE/REQUEST_CHANGES review", "mutating": True},
            {"name": "create_issue_comment", "description": "Comment on owned issue", "mutating": True},
            {"name": "get_pull", "description": "Get PR metadata", "mutating": False},
        ]

    def call(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        args = arguments or {}
        with factory_span(f"mcp.github.{name}", tool=name, agent="mcp-github"):
            if name == "create_pull_request":
                return self.create_pull_request(args)
            if name == "list_pull_reviews":
                return self.list_pull_reviews(args)
            if name == "submit_pull_review":
                return self.submit_pull_review(args)
            if name == "create_issue_comment":
                return self.create_issue_comment(args)
            if name == "get_pull":
                return self.get_pull(args)
            raise GitHubToolError(f"unknown tool: {name}")

    def create_pull_request(self, args: dict[str, Any]) -> dict[str, Any]:
        reject_shell_command_form(args.get("command") or args.get("shell") or args.get("gh_command"))
        owner = str(args.get("owner") or self.settings.github_owner)
        repo = str(args.get("repo") or self.settings.github_repo)
        assert_owned_repo(owner, repo, self.settings.github_owner, self.settings.github_repo)

        title = assert_no_shell_payload(str(args.get("title", "")).strip(), field="title")
        body = str(args.get("body") or "")
        # Body may contain markdown; still block env-injection / shell concat patterns.
        if "GITHUB_TOKEN=" in body or "$(env" in body.lower() or "`env`" in body:
            raise GitHubSecurityError("body: env / token injection denied")
        head = assert_owned_head_ref(
            str(args.get("head", "")),
            owner=self.settings.github_owner,
            repo=self.settings.github_repo,
        )
        base = assert_no_shell_payload(str(args.get("base") or "main").strip(), field="base")
        if not title:
            raise GitHubSecurityError("title is required")

        payload = {"title": title, "body": body, "head": head, "base": base}
        if self.settings.dry_run:
            return {"ok": True, "dry_run": True, "blocked": True, "reason": "dry_run", "would_create": payload}

        assert self.http is not None
        result = self.http.request("POST", f"/repos/{owner}/{repo}/pulls", json=payload)
        return {
            "ok": True,
            "dry_run": False,
            "number": result.get("number"),
            "html_url": result.get("html_url"),
            "head": head,
            "base": base,
        }

    def list_pull_reviews(self, args: dict[str, Any]) -> dict[str, Any]:
        owner = str(args.get("owner") or self.settings.github_owner)
        repo = str(args.get("repo") or self.settings.github_repo)
        assert_owned_repo(owner, repo, self.settings.github_owner, self.settings.github_repo)
        number = int(args.get("pull_number") or args.get("number") or 0)
        if number <= 0:
            raise GitHubSecurityError("pull_number is required")
        assert self.http is not None
        result = self.http.request("GET", f"/repos/{owner}/{repo}/pulls/{number}/reviews")
        reviews = result.get("_list", result if isinstance(result, list) else [])
        if isinstance(result, dict) and "_list" in result:
            reviews = result["_list"]
        elif isinstance(result, dict) and "ok" in result:
            reviews = []
        return {"ok": True, "pull_number": number, "reviews": reviews}

    def submit_pull_review(self, args: dict[str, Any]) -> dict[str, Any]:
        """Submit a PR review (APPROVE / REQUEST_CHANGES / COMMENT) — no shell concat."""
        reject_shell_command_form(args.get("command") or args.get("shell") or args.get("gh_command"))
        owner = str(args.get("owner") or self.settings.github_owner)
        repo = str(args.get("repo") or self.settings.github_repo)
        assert_owned_repo(owner, repo, self.settings.github_owner, self.settings.github_repo)
        number = int(args.get("pull_number") or args.get("number") or 0)
        if number <= 0:
            raise GitHubSecurityError("pull_number is required")
        event = str(args.get("event") or args.get("verdict") or "COMMENT").strip().upper().replace("-", "_")
        if event in {"APPROVED", "APPROVE"}:
            event = "APPROVE"
        elif event in {"CHANGES_REQUESTED", "REQUEST_CHANGES", "REQUESTCHANGES"}:
            event = "REQUEST_CHANGES"
        elif event not in {"APPROVE", "REQUEST_CHANGES", "COMMENT"}:
            raise GitHubSecurityError("event must be APPROVE, REQUEST_CHANGES, or COMMENT")
        body = str(args.get("body") or args.get("comment") or "")
        if "GITHUB_TOKEN=" in body:
            raise GitHubSecurityError("body: env / token injection denied")
        payload = {"event": event, "body": body}
        if self.settings.dry_run:
            return {
                "ok": True,
                "dry_run": True,
                "blocked": True,
                "reason": "dry_run",
                "would_review": payload,
                "pull_number": number,
            }
        assert self.http is not None
        result = self.http.request(
            "POST",
            f"/repos/{owner}/{repo}/pulls/{number}/reviews",
            json=payload,
        )
        return {
            "ok": True,
            "dry_run": False,
            "id": result.get("id"),
            "state": result.get("state") or event,
            "html_url": result.get("html_url"),
            "pull_number": number,
        }
    def create_issue_comment(self, args: dict[str, Any]) -> dict[str, Any]:
        owner = str(args.get("owner") or self.settings.github_owner)
        repo = str(args.get("repo") or self.settings.github_repo)
        assert_owned_repo(owner, repo, self.settings.github_owner, self.settings.github_repo)
        number = int(args.get("issue_number") or args.get("number") or 0)
        body = str(args.get("body") or "")
        if number <= 0 or not body.strip():
            raise GitHubSecurityError("issue_number and body are required")
        if "GITHUB_TOKEN=" in body:
            raise GitHubSecurityError("body: env / token injection denied")
        payload = {"body": body}
        if self.settings.dry_run:
            return {"ok": True, "dry_run": True, "blocked": True, "reason": "dry_run", "would_comment": payload}
        assert self.http is not None
        result = self.http.request(
            "POST",
            f"/repos/{owner}/{repo}/issues/{number}/comments",
            json=payload,
        )
        return {"ok": True, "id": result.get("id"), "html_url": result.get("html_url")}

    def get_pull(self, args: dict[str, Any]) -> dict[str, Any]:
        owner = str(args.get("owner") or self.settings.github_owner)
        repo = str(args.get("repo") or self.settings.github_repo)
        assert_owned_repo(owner, repo, self.settings.github_owner, self.settings.github_repo)
        number = int(args.get("pull_number") or args.get("number") or 0)
        if number <= 0:
            raise GitHubSecurityError("pull_number is required")
        assert self.http is not None
        result = self.http.request("GET", f"/repos/{owner}/{repo}/pulls/{number}")
        return {"ok": True, "pull": result}
