"""Minimal Kind OSS status board — polls sibling /health endpoints."""

from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

TARGETS = [
    ("inference-gateway", "http://asf-inference-gateway:8081/health"),
    ("orchestrator", "http://asf-orchestrator:8080/health"),
    ("agent-pm", "http://asf-agent-pm:8080/health"),
    ("agent-architect", "http://asf-agent-architect:8080/health"),
    ("agent-developer", "http://asf-agent-developer:8080/health"),
    ("agent-reviewer", "http://asf-agent-reviewer:8080/health"),
    ("agent-security", "http://asf-agent-security:8080/health"),
    ("agent-qa", "http://asf-agent-qa:8080/health"),
    ("agent-documentation", "http://asf-agent-documentation:8080/health"),
    ("agent-deployment", "http://asf-agent-deployment:8080/health"),
    ("agent-sre", "http://asf-agent-sre:8080/health"),
    ("mcp-github", "http://asf-mcp-github:8091/health"),
    ("mcp-filesystem", "http://asf-mcp-filesystem:8092/health"),
    ("mcp-git", "http://asf-mcp-git:8093/health"),
    ("mcp-kubernetes", "http://asf-mcp-kubernetes:8095/health"),
    ("sample-app", "http://sample-app:8080/health"),
]


def create_app() -> FastAPI:
    app = FastAPI(title="ASF Kind status", version="0.1.0")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "asf-status"}

    @app.get("/api/status")
    async def api_status() -> dict[str, Any]:
        timeout = float(os.environ.get("STATUS_TIMEOUT", "2"))
        results: list[dict[str, Any]] = []

        async with httpx.AsyncClient(timeout=timeout) as client:

            async def one(name: str, url: str) -> dict[str, Any]:
                try:
                    r = await client.get(url)
                    body: Any
                    try:
                        body = r.json()
                    except Exception:
                        body = r.text[:200]
                    return {"name": name, "url": url, "ok": r.is_success, "status_code": r.status_code, "body": body}
                except Exception as exc:  # noqa: BLE001 — surface probe errors
                    return {"name": name, "url": url, "ok": False, "error": str(exc)}

            results = list(await asyncio.gather(*[one(n, u) for n, u in TARGETS]))
        return {
            "ok_count": sum(1 for x in results if x.get("ok")),
            "total": len(results),
            "services": results,
        }

    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        data = await api_status()
        rows = []
        for s in data["services"]:
            color = "#1a7f37" if s.get("ok") else "#cf222e"
            detail = s.get("status_code") or s.get("error") or ""
            rows.append(
                f"<tr><td>{s['name']}</td><td style='color:{color}'>"
                f"{'UP' if s.get('ok') else 'DOWN'}</td><td>{detail}</td></tr>"
            )
        return f"""<!doctype html>
<html><head><meta charset="utf-8"/><title>ASF Kind status</title>
<meta http-equiv="refresh" content="5"/>
<style>
 body{{font-family:ui-sans-serif,system-ui,sans-serif;margin:2rem;background:#0d1117;color:#e6edf3}}
 table{{border-collapse:collapse;width:100%;max-width:900px}}
 th,td{{border-bottom:1px solid #30363d;padding:.5rem .75rem;text-align:left}}
 h1{{margin-top:0}} .meta{{color:#8b949e}}
</style></head>
<body>
<h1>AI Software Factory — Kind</h1>
<p class="meta">{data['ok_count']}/{data['total']} healthy · auto-refresh 5s · PROFILE=kind-oss</p>
<table><thead><tr><th>Service</th><th>State</th><th>Detail</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
</body></html>"""

    return app


app = create_app()
