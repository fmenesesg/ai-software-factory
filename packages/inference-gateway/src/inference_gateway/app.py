"""FastAPI OpenAI-compatible inference gateway — live Granite + emergency fallback."""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from agent_sdk.otel import ATTRS, factory_span, record_token_usage
from inference_gateway.config import GatewaySettings


def create_app(settings: GatewaySettings | None = None) -> FastAPI:
    settings = settings or GatewaySettings()
    app = FastAPI(title="AI Software Factory Inference Gateway", version="0.6.0")
    app.state.settings = settings

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "stub_mode": settings.stub_mode,
            "upstream_configured": bool(settings.upstream_url),
            "model": settings.upstream_model,
            "inference_fallback": settings.inference_fallback,
            "fallback_label": "emergency-only",
        }

    @app.post("/v1/chat/completions")
    async def chat_completions(request: Request) -> JSONResponse:
        body = await request.json()
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="JSON object required")
        model = body.get("model") or settings.upstream_model
        messages = body.get("messages") or []
        run_id = None
        if isinstance(body.get("factory"), dict):
            run_id = body["factory"].get("run_id")

        if settings.stub_mode:
            result = _stub_completion(model=model, messages=messages, fallback=False)
            _emit_inference_span(
                run_id=run_id,
                model=model,
                fallback=False,
                usage=result.get("usage") or {},
            )
            return JSONResponse(result)

        return JSONResponse(await _proxy_upstream(settings, body, model=model, run_id=run_id))

    return app


def _emit_inference_span(
    *,
    run_id: str | None,
    model: str,
    fallback: bool,
    usage: dict[str, Any],
) -> None:
    """Record inference.chat span with workshop.fallback / inference.fallback attrs."""
    with factory_span(
        "inference.chat",
        run_id=run_id or "gateway",
        model_id=model,
        fallback=fallback,
        stage="inference",
        attributes={ATTRS.FALLBACK: bool(fallback), "inference.fallback": bool(fallback)},
    ) as span:
        record_token_usage(
            span,
            prompt_tokens=int(usage.get("prompt_tokens") or 0) or None,
            completion_tokens=int(usage.get("completion_tokens") or 0) or None,
            total_tokens=int(usage.get("total_tokens") or 0) or None,
        )


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
    if fallback:
        content = (
            "[EMERGENCY FALLBACK — not primary narrative] Recorded/local response "
            f"(model={model}). Live Granite unreachable. Echo: {last_user[:200]}"
        )
    else:
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
        "factory": {
            "fallback": fallback,
            "stub": True,
            "fallback_label": "emergency-only" if fallback else None,
        },
    }


async def _proxy_upstream(
    settings: GatewaySettings,
    body: dict[str, Any],
    *,
    model: str,
    run_id: str | None = None,
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
                    # Live Granite path MUST surface usage tokens (normalize if upstream omits).
                    data["usage"] = _ensure_usage(data.get("usage"), body.get("messages"), data)
                    data["model"] = data.get("model") or model
                    _emit_inference_span(
                        run_id=run_id,
                        model=str(data.get("model") or model),
                        fallback=False,
                        usage=data.get("usage") or {},
                    )
                return data
            except (httpx.HTTPError, httpx.TimeoutException) as exc:
                last_error = exc
                if attempt + 1 < attempts:
                    await asyncio.sleep(0.05 * (attempt + 1))

    if settings.inference_fallback:
        messages = body.get("messages") if isinstance(body.get("messages"), list) else []
        result = _stub_completion(model=model, messages=messages, fallback=True)
        result["factory"] = {
            "fallback": True,
            "stub": True,
            "fallback_label": "emergency-only",
            "upstream_error": str(last_error),
        }
        _emit_inference_span(
            run_id=run_id,
            model=model,
            fallback=True,
            usage=result.get("usage") or {},
        )
        return result

    raise HTTPException(
        status_code=502,
        detail=f"upstream inference failed after retries: {last_error}",
    )


def _ensure_usage(
    usage: Any,
    messages: Any,
    data: dict[str, Any],
) -> dict[str, int]:
    """Guarantee prompt/completion/total token fields on completions."""
    if isinstance(usage, dict):
        prompt = int(usage.get("prompt_tokens") or 0)
        completion = int(usage.get("completion_tokens") or 0)
        total = int(usage.get("total_tokens") or (prompt + completion))
        if total > 0 or prompt > 0 or completion > 0:
            return {
                "prompt_tokens": prompt or max(1, len(str(messages)) // 4),
                "completion_tokens": completion
                or max(
                    1,
                    len(str(((data.get("choices") or [{}])[0] or {}).get("message", {}))) // 4,
                ),
                "total_tokens": total
                or (
                    (prompt or max(1, len(str(messages)) // 4))
                    + (
                        completion
                        or max(
                            1,
                            len(str(((data.get("choices") or [{}])[0] or {}).get("message", {})))
                            // 4,
                        )
                    )
                ),
            }
    prompt_tokens = max(1, len(str(messages)) // 4)
    content = ""
    choices = data.get("choices") if isinstance(data.get("choices"), list) else []
    if choices and isinstance(choices[0], dict):
        message = choices[0].get("message") or {}
        if isinstance(message, dict):
            content = str(message.get("content") or "")
    completion_tokens = max(1, len(content) // 4)
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
    }


app = create_app()
