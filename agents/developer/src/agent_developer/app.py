"""Developer agent — Quarkus Hello World via MCP fs/git/github (Kind OSS live path)."""

from __future__ import annotations

import os
import re
from typing import Any

from fastapi import FastAPI

from agent_sdk.inference import InferenceClient, InferenceClientConfig
from agent_sdk.mcp import McpClient, McpClientConfig
from agent_sdk.otel import factory_span
from agent_sdk.runtime import AgentInvokeRequest, AgentInvokeResponse, env_bool, env_gateway_url, env_model_id

from agent_developer.quarkus_hello import quarkus_hello_files

_ISSUE_NUM_RE = re.compile(r"/issues/(\d+)")


def _env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).rstrip("/")


def _mcp_url(name: str, default: str) -> str:
    return _env(name, default)


def create_app() -> FastAPI:
    app = FastAPI(title="AI Software Factory Developer Agent", version="0.3.0")
    app.state.agent_name = "developer"

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "agent": "developer",
            "live_mcp": not env_bool("AGENT_DEVELOPER_STUB_PR", False),
        }

    @app.post("/v1/invoke", response_model=AgentInvokeResponse)
    async def invoke(body: AgentInvokeRequest) -> AgentInvokeResponse:
        artifacts = dict(body.artifacts)
        approval_id = artifacts.get("architect_approval_id")
        design_path = artifacts.get("design_path")
        issue_url = str(artifacts.get("issue_url") or "")

        if not approval_id:
            return AgentInvokeResponse(
                agent="developer",
                run_id=body.run_id,
                status="blocked",
                artifacts=artifacts,
                message="Developer blocked: architect_approval_id required (GitHub HITL)",
            )
        if not design_path or not issue_url:
            return AgentInvokeResponse(
                agent="developer",
                run_id=body.run_id,
                status="error",
                artifacts=artifacts,
                message="design_path and issue_url are required",
            )

        with factory_span("agent.developer.invoke", run_id=body.run_id, agent="developer", stage="developer"):
            message = body.input.get("summary")
            usage = None
            if message is None and not env_bool("AGENT_SKIP_INFERENCE", False):
                async with InferenceClient(
                    InferenceClientConfig(gateway_url=env_gateway_url(), model=env_model_id())
                ) as client:
                    completion = await client.chat_completions(
                        [
                            {
                                "role": "system",
                                "content": "You are the Developer agent. Summarize the PR to open.",
                            },
                            {
                                "role": "user",
                                "content": (
                                    f"Issue: {issue_url}\nDesign: {design_path}\n"
                                    f"Approval: {approval_id}"
                                ),
                            },
                        ]
                    )
                message = completion["choices"][0]["message"]["content"]
                raw_usage = completion.get("usage") or {}
                usage = {
                    "prompt_tokens": int(raw_usage.get("prompt_tokens") or 0),
                    "completion_tokens": int(raw_usage.get("completion_tokens") or 0),
                    "total_tokens": int(raw_usage.get("total_tokens") or 0),
                }

            # Explicit stub / offline: keep placeholder PR URL (unit tests).
            if env_bool("AGENT_DEVELOPER_STUB_PR", False) or body.input.get("pr_url"):
                pr_url = artifacts.get("pr_url") or body.input.get("pr_url")
                if not pr_url:
                    owner = body.input.get("owner") or _env("GITHUB_OWNER", "fmenesesg")
                    repo = body.input.get("repo") or _env("GITHUB_REPO", "asf-demo-app")
                    pr_number = body.input.get("pr_number") or body.run_id
                    pr_url = f"https://github.com/{owner}/{repo}/pull/{pr_number}"
                artifacts["pr_url"] = pr_url
                if message is None:
                    message = f"PR {pr_url} from approved design {design_path}"
                return AgentInvokeResponse(
                    agent="developer",
                    run_id=body.run_id,
                    status="ok",
                    artifacts=artifacts,
                    message=str(message)[:2000],
                    usage=usage,
                )

            try:
                pr_url, detail = await _live_quarkus_pr(
                    run_id=body.run_id,
                    issue_url=issue_url,
                    design_path=str(design_path),
                    approval_id=str(approval_id),
                    summary=str(message or ""),
                )
            except Exception as exc:  # noqa: BLE001 — surface MCP failures to orchestrator
                return AgentInvokeResponse(
                    agent="developer",
                    run_id=body.run_id,
                    status="error",
                    artifacts=artifacts,
                    message=f"live MCP PR failed: {type(exc).__name__}: {exc}",
                    usage=usage,
                )

            artifacts["pr_url"] = pr_url
            artifacts["developer_branch"] = detail.get("branch")
            if message is None:
                message = detail.get("message") or f"Opened {pr_url}"
            return AgentInvokeResponse(
                agent="developer",
                run_id=body.run_id,
                status="ok",
                artifacts=artifacts,
                message=str(message)[:2000],
                usage=usage,
            )

    return app


async def _live_quarkus_pr(
    *,
    run_id: str,
    issue_url: str,
    design_path: str,
    approval_id: str,
    summary: str,
) -> tuple[str, dict[str, Any]]:
    owner = _env("GITHUB_OWNER", "fmenesesg")
    repo = _env("GITHUB_REPO", "asf-demo-app")
    workspace = _env("WORKSPACE_ROOT", "/workspace") or "/workspace"
    repo_dirname = repo
    repo_path = f"{workspace.rstrip('/')}/{repo_dirname}"
    issue_num = _ISSUE_NUM_RE.search(issue_url)
    branch = f"feat/issue-{issue_num.group(1) if issue_num else 'x'}-{run_id[-8:]}"
    files = quarkus_hello_files(run_id=run_id, issue_url=issue_url)
    rel_paths = sorted(files.keys())

    fs_url = _mcp_url("MCP_FILESYSTEM_URL", "http://asf-mcp-filesystem:8092")
    git_url = _mcp_url("MCP_GIT_URL", "http://asf-mcp-git:8093")
    gh_url = _mcp_url("MCP_GITHUB_URL", "http://asf-mcp-github:8091")

    async with (
        McpClient(McpClientConfig(base_url=fs_url, server_name="filesystem")) as fs,
        McpClient(McpClientConfig(base_url=git_url, server_name="git")) as git,
        McpClient(McpClientConfig(base_url=gh_url, server_name="github")) as gh,
    ):
        clone = await git.call_tool(
            "git_clone",
            {"dirname": repo_dirname},
            mutating=True,
        )
        if not clone.ok:
            raise RuntimeError(clone.error or "git_clone failed")
        content = clone.content if isinstance(clone.content, dict) else {}
        if content.get("blocked"):
            raise RuntimeError("git_clone blocked (DRY_RUN?)")
        repo_path = str(content.get("repo_path") or repo_path)

        co = await git.call_tool(
            "git_checkout",
            {"repo_path": repo_path, "branch": branch},
            mutating=True,
        )
        if not co.ok:
            raise RuntimeError(co.error or "git_checkout failed")

        for rel, body in files.items():
            # Paths relative to workspace_root for filesystem MCP.
            ws_rel = f"{repo_dirname}/{rel}"
            wr = await fs.call_tool(
                "fs_write",
                {"path": ws_rel, "content": body},
                mutating=True,
            )
            if not wr.ok:
                raise RuntimeError(wr.error or f"fs_write failed: {ws_rel}")
            wr_content = wr.content if isinstance(wr.content, dict) else {}
            if wr_content.get("blocked"):
                raise RuntimeError(f"fs_write blocked (DRY_RUN?): {ws_rel}")

        add = await git.call_tool(
            "git_add",
            {"repo_path": repo_path, "paths": rel_paths},
            mutating=True,
        )
        if not add.ok:
            raise RuntimeError(add.error or "git_add failed")

        commit_msg = f"feat: Quarkus Hello World for {run_id}"
        cm = await git.call_tool(
            "git_commit",
            {
                "repo_path": repo_path,
                "message": commit_msg,
                "staged_paths": rel_paths,
            },
            mutating=True,
        )
        if not cm.ok:
            raise RuntimeError(cm.error or "git_commit failed")

        push_ref = f"HEAD:refs/heads/{branch}"
        push = await git.call_tool(
            "git_push",
            {"repo_path": repo_path, "ref": push_ref},
            mutating=True,
        )
        if not push.ok:
            raise RuntimeError(push.error or "git_push failed")
        push_content = push.content if isinstance(push.content, dict) else {}
        if push_content.get("blocked"):
            raise RuntimeError("git_push blocked (DRY_RUN?)")

        title = f"feat: Quarkus Hello World ({run_id})"
        body = "\n".join(
            [
                "## Summary",
                "",
                summary or "Deterministic Quarkus Hello World scaffold from Developer agent.",
                "",
                f"- Issue: {issue_url}",
                f"- Design: `{design_path}`",
                f"- Architect approval: `{approval_id}`",
                f"- Branch: `{branch}`",
                "",
                "### Acceptance",
                "",
                "- `GET /hello` returns `Hello from ASF`",
                "- Quarkus 3.x / Java 17+",
            ]
        )
        pr = await gh.call_tool(
            "create_pull_request",
            {
                "owner": owner,
                "repo": repo,
                "title": title,
                "body": body,
                "head": branch,
                "base": "main",
            },
            mutating=True,
        )
        if not pr.ok:
            raise RuntimeError(pr.error or "create_pull_request failed")
        pr_content = pr.content if isinstance(pr.content, dict) else {}
        if pr_content.get("blocked"):
            raise RuntimeError("create_pull_request blocked (DRY_RUN?)")
        pr_url = str(pr_content.get("html_url") or "")
        if not pr_url:
            raise RuntimeError(f"create_pull_request missing html_url: {pr_content}")

    return pr_url, {"branch": branch, "message": f"Opened {pr_url}", "paths": rel_paths}


app = create_app()
