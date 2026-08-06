"""FastAPI OpenAI-compatible inference gateway skeleton."""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from inference_gateway.config import GatewaySettings


def create_app(settings: GatewaySettings | None = None) -> FastAPI:
    settings = settings or GatewaySettings()
    app = FastAPI(title="AI Software Factory Inference Gateway", version="0.1.0")
    app.state.settings = settings

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "stub_mode": settings.stub_mode,
            "upstream_configured": bool(settings.upstream_url),
            "model": settings.upstream_model,
        }

    @app.post("/v1/chat/completions")
    async def chat_completions(request: Request) -> JSONResponse:
        body = await request.json()
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="JSON object required")
        model = body.get("model") or settings.upstream_model
        messages = body.get("messages") or []

        if settings.stub_mode:
            return JSONResponse(_stub_completion(model=model, messages=messages, fallback=False))

        return JSONResponse(await _proxy_upstream(settings, body, model=model))

    return app


def _stub_completion(
    *,
    model: str,
    messages: list[Any],
    fallback: bool,
) -> dict[str, Any]:
    last_user = ""
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "user":
            last_user = str(msg.get("content", ""))
            break
    content = (
        "[inference-gateway stub] Live Granite path is configured via OSAI_* "
        f"(model={model}). Echo: {last_user[:200]}"
    )
    prompt_tokens = max(1, len(str(messages)) // 4)
    completion_tokens = max(1, len(content) // 4)
    return {
        "id": f"chatcmpl-stub-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
        "factory": {"fallback": fallback, "stub": True},
    }


async def _proxy_upstream(
    settings: GatewaySettings,
    body: dict[str, Any],
    *,
    model: str,
) -> dict[str, Any]:
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if settings.upstream_api_key:
        headers["Authorization"] = f"Bearer {settings.upstream_api_key}"

    url = settings.upstream_url.rstrip("/") + "/chat/completions"
    # If upstream already includes /v1, avoid double-append confusion:
    if settings.upstream_url.rstrip("/").endswith("/v1"):
        url = settings.upstream_url.rstrip("/") + "/chat/completions"
    elif "/v1/" not in settings.upstream_url:
        url = settings.upstream_url.rstrip("/") + "/v1/chat/completions"

    payload = {**body, "model": model}
    last_error: Exception | None = None
    attempts = max(1, settings.max_retries + 1)

    async with httpx.AsyncClient(timeout=settings.timeout_seconds) as client:
        for attempt in range(attempts):
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                if isinstance(data, dict):
                    data.setdefault("factory", {})
                    if isinstance(data["factory"], dict):
                        data["factory"]["fallback"] = False
                        data["factory"]["stub"] = False
                return data
            except (httpx.HTTPError, httpx.TimeoutException) as exc:
                last_error = exc
                if attempt + 1 < attempts:
                    await asyncio.sleep(0.05 * (attempt + 1))

    if settings.inference_fallback:
        messages = body.get("messages") if isinstance(body.get("messages"), list) else []
        result = _stub_completion(model=model, messages=messages, fallback=True)
        result["factory"] = {"fallback": True, "stub": True, "upstream_error": str(last_error)}
        return result

    raise HTTPException(
        status_code=502,
        detail=f"upstream inference failed after retries: {last_error}",
    )


app = create_app()
