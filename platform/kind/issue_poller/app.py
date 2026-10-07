"""Poll GitHub Issues with label asf/run and start orchestrator runs."""

from __future__ import annotations

import asyncio
import os
import re
import uuid
from typing import Any

import httpx
from fastapi import FastAPI

ASF_RUN_MARKER = "asf-run-id:"
LABEL = os.environ.get("ASF_ISSUE_LABEL", "asf/run")
POLL_SECONDS = float(os.environ.get("ASF_ISSUE_POLL_SECONDS", "15"))
ORCH_URL = os.environ.get("ORCHESTRATOR_URL", "http://asf-orchestrator:8080").rstrip("/")
GITHUB_API = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
OWNER = os.environ.get("GITHUB_OWNER", "fmenesesg")
REPO = os.environ.get("GITHUB_REPO", "asf-demo-app")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
STATUS_BASE = os.environ.get("ASF_STATUS_PUBLIC_URL", "http://asf.demo.local:8080")
JAEGER_PUBLIC_URL = os.environ.get(
    "ASF_JAEGER_PUBLIC_URL", "http://jaeger.asf.demo.local:8080"
)


def create_app() -> FastAPI:
    app = FastAPI(title="ASF Issue Poller", version="0.1.0")
    app.state.seen: set[str] = set()
    app.state.resumed: set[str] = set()
    app.state.task = None

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "label": LABEL,
            "owner": OWNER,
            "repo": REPO,
            "token_configured": bool(TOKEN) and TOKEN != "kind-local-unused",
            "poll_seconds": POLL_SECONDS,
        }

    @app.on_event("startup")
    async def _start() -> None:
        app.state.task = asyncio.create_task(_poll_loop(app))

    @app.on_event("shutdown")
    async def _stop() -> None:
        if app.state.task:
            app.state.task.cancel()

    return app


async def _poll_loop(app: FastAPI) -> None:
    while True:
        try:
            await _tick(app)
            await _resume_hitl(app)
        except Exception as exc:  # noqa: BLE001
            print(f"issue-poller error: {type(exc).__name__}: {exc!r}", flush=True)
        await asyncio.sleep(POLL_SECONDS)


def _headers() -> dict[str, str]:
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if TOKEN and TOKEN != "kind-local-unused":
        h["Authorization"] = f"Bearer {TOKEN}"
    return h


async def _tick(app: FastAPI) -> None:
    if not TOKEN or TOKEN == "kind-local-unused":
        return
    url = f"{GITHUB_API}/repos/{OWNER}/{REPO}/issues"
    params = {"state": "open", "labels": LABEL, "per_page": "30"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, headers=_headers(), params=params)
        if resp.status_code >= 400:
            print(f"list issues failed: {resp.status_code} {resp.text[:200]}", flush=True)
            return
        issues = resp.json()
        if not isinstance(issues, list):
            return
        for issue in issues:
            if issue.get("pull_request"):
                continue
            number = issue.get("number")
            html_url = issue.get("html_url") or ""
            key = f"{OWNER}/{REPO}#{number}"
            if key in app.state.seen:
                continue
            # Skip if already annotated.
            comments_url = issue.get("comments_url")
            if comments_url:
                cr = await client.get(comments_url, headers=_headers())
                bodies = " ".join(
                    c.get("body") or "" for c in (cr.json() if cr.status_code < 400 else [])
                )
                if ASF_RUN_MARKER in bodies or ASF_RUN_MARKER in (issue.get("body") or ""):
                    app.state.seen.add(key)
                    continue
            run_id = f"issue-{number}-{uuid.uuid4().hex[:8]}"
            start = await client.post(
                f"{ORCH_URL}/v1/runs",
                json={
                    "run_id": run_id,
                    "artifacts": {"issue_url": html_url},
                },
            )
            if start.status_code >= 400:
                print(f"start run failed: {start.status_code} {start.text[:200]}", flush=True)
                continue
            body = (
                f"{ASF_RUN_MARKER} `{run_id}`\n"
                f"- status: {STATUS_BASE}/status/\n"
                f"- jaeger: {JAEGER_PUBLIC_URL}/\n"
                f"- tekton: http://tekton.asf.demo.local:8080/\n"
                f"- orchestrator stage: `{(start.json() or {}).get('stage')}`\n"
            )
            await client.post(
                f"{GITHUB_API}/repos/{OWNER}/{REPO}/issues/{number}/comments",
                headers=_headers(),
                json={"body": body},
            )
            app.state.seen.add(key)
            print(f"started run {run_id} for issue #{number}", flush=True)


async def _issue_comment_match(
    client: httpx.AsyncClient, issue_url: str, pattern: str
) -> str | None:
    m = re.search(r"/issues/(\d+)", issue_url)
    if not m or not TOKEN or TOKEN == "kind-local-unused":
        return None
    cr = await client.get(
        f"{GITHUB_API}/repos/{OWNER}/{REPO}/issues/{m.group(1)}/comments",
        headers=_headers(),
    )
    if cr.status_code >= 400:
        return None
    for c in cr.json():
        am = re.search(pattern, c.get("body") or "")
        if am:
            return am.group(1)
    return None


async def _resume_hitl(app: FastAPI) -> None:
    """Resume Architect / promote HITL from env or Issue comments (asf-approve / asf-promote)."""
    static_arch = os.environ.get("HITL_STATIC_APPROVAL_ID")
    static_promo = os.environ.get("HITL_STATIC_PROMOTE_APPROVAL_ID")
    async with httpx.AsyncClient(timeout=30.0) as client:
        listed = await client.get(f"{ORCH_URL}/v1/runs")
        if listed.status_code >= 400:
            return
        runs = (listed.json() or {}).get("runs") or []
        for run in runs:
            stage = run.get("stage")
            run_id = run.get("run_id")
            arts = dict(run.get("artifacts") or {})
            issue_url = str(arts.get("issue_url") or "")

            if stage == "hitl_waiting" and not arts.get("architect_approval_id"):
                resume_key = f"arch:{run_id}"
                if resume_key in app.state.resumed:
                    continue
                approval = static_arch or await _issue_comment_match(
                    client, issue_url, r"asf-approve:\s*(\S+)"
                )
                if not approval:
                    continue
                resume_id = f"{run_id}-resume"
                print(f"resuming architect HITL for {run_id} approval={approval}", flush=True)
                resp = await client.post(
                    f"{ORCH_URL}/v1/runs",
                    json={
                        "run_id": resume_id,
                        "architect_approval_id": approval,
                        "artifacts": arts,
                    },
                )
                app.state.resumed.add(resume_key)
                print(
                    f"architect resume {resp.status_code} stage={(resp.json() or {}).get('stage')}",
                    flush=True,
                )
                continue

            if stage == "promote_waiting" and not arts.get("promote_approval_id"):
                resume_key = f"promo:{run_id}"
                if resume_key in app.state.resumed:
                    continue
                promo = static_promo or await _issue_comment_match(
                    client, issue_url, r"asf-promote:\s*(\S+)"
                )
                if not promo:
                    continue
                # Keep architect approval so the graph can pass the earlier gate.
                resume_id = f"{run_id}-promote"
                print(f"resuming promote HITL for {run_id} approval={promo}", flush=True)
                resp = await client.post(
                    f"{ORCH_URL}/v1/runs",
                    json={
                        "run_id": resume_id,
                        "architect_approval_id": arts.get("architect_approval_id")
                        or static_arch
                        or "demo-approval-1",
                        "promote_approval_id": promo,
                        "artifacts": arts,
                    },
                )
                app.state.resumed.add(resume_key)
                print(
                    f"promote resume {resp.status_code} stage={(resp.json() or {}).get('stage')}",
                    flush=True,
                )


app = create_app()
