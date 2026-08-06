"""RED: PR commands — no shell concat; deny --head spoof / env injection."""

from __future__ import annotations

import pytest

from mcp_github.config import GitHubMcpSettings
from mcp_github.security import GitHubSecurityError
from mcp_github.tools import GitHubTools, InMemoryGitHubHttp


def _tools() -> tuple[GitHubTools, InMemoryGitHubHttp]:
    settings = GitHubMcpSettings(
        github_owner="fmenesesg",
        github_repo="ai-software-factory",
        dry_run=False,
    )
    http = InMemoryGitHubHttp()
    return GitHubTools(settings, http=http), http


def test_deny_shell_gh_command_concat() -> None:
    tools, http = _tools()
    with pytest.raises(GitHubSecurityError, match="shell|concat"):
        tools.create_pull_request(
            {
                "command": "gh pr create --title x --head evil:main",
                "title": "x",
                "head": "feat/ok",
            }
        )
    assert http.calls == []


def test_deny_head_flag_spoof() -> None:
    tools, _ = _tools()
    with pytest.raises(GitHubSecurityError, match="CLI flag|--head"):
        tools.create_pull_request({"title": "x", "head": "--head evil:main"})


def test_deny_cross_owner_head_spoof() -> None:
    tools, http = _tools()
    with pytest.raises(GitHubSecurityError, match="spoof|cross-owner"):
        tools.create_pull_request({"title": "x", "head": "attacker:malicious-branch"})
    assert http.calls == []


def test_deny_env_injection_in_title() -> None:
    tools, http = _tools()
    with pytest.raises(GitHubSecurityError, match="env|injection|shell"):
        tools.create_pull_request(
            {
                "title": "feat; export GITHUB_TOKEN=leak",
                "head": "feat/ok",
            }
        )
    assert http.calls == []


def test_deny_env_prefix_injection_in_body() -> None:
    tools, http = _tools()
    with pytest.raises(GitHubSecurityError, match="injection"):
        tools.create_pull_request(
            {
                "title": "feat ok",
                "head": "feat/ok",
                "body": "see GITHUB_TOKEN=should-not-appear",
            }
        )
    assert http.calls == []


def test_structured_pr_create_uses_api_not_shell() -> None:
    tools, http = _tools()
    result = tools.create_pull_request(
        {
            "title": "feat: m2 slice",
            "head": "feat/m2-granite-mcp-hitl",
            "base": "main",
            "body": "Closes #1",
        }
    )
    assert result["ok"] is True
    assert len(http.calls) == 1
    call = http.calls[0]
    assert call["method"] == "POST"
    assert call["path"] == "/repos/fmenesesg/ai-software-factory/pulls"
    assert call["json"]["head"] == "feat/m2-granite-mcp-hitl"
    assert "gh " not in str(call)


def test_dry_run_blocks_pr_write() -> None:
    settings = GitHubMcpSettings(
        github_owner="fmenesesg",
        github_repo="ai-software-factory",
        dry_run=True,
    )
    http = InMemoryGitHubHttp()
    tools = GitHubTools(settings, http=http)
    result = tools.create_pull_request(
        {"title": "feat: dry", "head": "feat/x", "base": "main", "body": "n/a"}
    )
    assert result["blocked"] is True
    assert result["dry_run"] is True
    assert http.calls == []


def test_deny_wrong_repo_scope() -> None:
    tools, _ = _tools()
    with pytest.raises(GitHubSecurityError, match="repo scope"):
        tools.create_pull_request(
            {
                "owner": "other",
                "repo": "place",
                "title": "x",
                "head": "feat/x",
            }
        )
