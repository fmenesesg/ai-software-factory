"""Inference client — agents call the gateway only (no direct OSAI URLs)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass(slots=True)
class InferenceClientConfig:
    """OpenAI-compatible gateway settings (never point agents at OSAI directly)."""

    gateway_url: str
    model: str | None = None
    api_key: str | None = None
    timeout_seconds: float = 60.0
    max_retries: int = 2


@dataclass
class InferenceClient:
    """Thin OpenAI-compatible chat completions client aimed at inference-gateway."""

    config: InferenceClientConfig
    _client: httpx.AsyncClient | None = field(default=None, init=False, repr=False)

    async def __aenter__(self) -> InferenceClient:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        self._client = httpx.AsyncClient(
            base_url=self.config.gateway_url.rstrip("/"),
            headers=headers,
            timeout=self.config.timeout_seconds,
        )
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def chat_completions(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str | None = None,
        **extra: Any,
    ) -> dict[str, Any]:
        if self._client is None:
            raise RuntimeError("InferenceClient must be used as an async context manager")
        body: dict[str, Any] = {
            "model": model or self.config.model or "ibm/granite-*-instruct",
            "messages": messages,
            **extra,
        }
        last_error: Exception | None = None
        attempts = max(1, self.config.max_retries + 1)
        for _ in range(attempts):
            try:
                response = await self._client.post("/v1/chat/completions", json=body)
                response.raise_for_status()
                return response.json()
            except (httpx.HTTPError, httpx.TimeoutException) as exc:
                last_error = exc
        assert last_error is not None
        raise last_error
