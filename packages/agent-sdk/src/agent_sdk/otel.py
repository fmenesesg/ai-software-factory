"""OpenTelemetry helpers for factory spans (ADR-010)."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator

from opentelemetry import trace
from opentelemetry.trace import Span, Status, StatusCode


@dataclass(frozen=True, slots=True)
class FactorySpanAttrs:
    """Canonical attribute names for workshop observability."""

    RUN_ID: str = "workshop.run_id"
    AGENT_NAME: str = "workshop.agent"
    TOOL_NAME: str = "workshop.tool"
    MODEL_ID: str = "workshop.model_id"
    TOKENS_PROMPT: str = "workshop.tokens.prompt"
    TOKENS_COMPLETION: str = "workshop.tokens.completion"
    TOKENS_TOTAL: str = "workshop.tokens.total"
    FALLBACK: str = "workshop.fallback"
    STAGE: str = "workshop.stage"
    PROFILE: str = "workshop.profile"


ATTRS = FactorySpanAttrs()


def start_factory_span(
    name: str,
    *,
    run_id: str | None = None,
    agent: str | None = None,
    tool: str | None = None,
    model_id: str | None = None,
    fallback: bool | None = None,
    stage: str | None = None,
    attributes: dict[str, Any] | None = None,
) -> Span:
    """Start a child span with factory attribute conventions (no secret values)."""
    tracer = trace.get_tracer("ai-software-factory")
    span = tracer.start_span(name)
    if run_id is not None:
        span.set_attribute(ATTRS.RUN_ID, run_id)
    if agent is not None:
        span.set_attribute(ATTRS.AGENT_NAME, agent)
    if tool is not None:
        span.set_attribute(ATTRS.TOOL_NAME, tool)
    if model_id is not None:
        span.set_attribute(ATTRS.MODEL_ID, model_id)
    if fallback is not None:
        span.set_attribute(ATTRS.FALLBACK, bool(fallback))
    if stage is not None:
        span.set_attribute(ATTRS.STAGE, stage)
    if attributes:
        for key, value in attributes.items():
            if value is None:
                continue
            # Never attach values that look like secrets.
            lowered = key.lower()
            if any(s in lowered for s in ("token", "password", "secret", "authorization", "api_key")):
                if key not in {
                    ATTRS.TOKENS_PROMPT,
                    ATTRS.TOKENS_COMPLETION,
                    ATTRS.TOKENS_TOTAL,
                }:
                    continue
            span.set_attribute(key, value)
    return span


def record_token_usage(
    span: Span,
    *,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    total_tokens: int | None = None,
) -> None:
    if prompt_tokens is not None:
        span.set_attribute(ATTRS.TOKENS_PROMPT, int(prompt_tokens))
    if completion_tokens is not None:
        span.set_attribute(ATTRS.TOKENS_COMPLETION, int(completion_tokens))
    if total_tokens is not None:
        span.set_attribute(ATTRS.TOKENS_TOTAL, int(total_tokens))


@contextmanager
def factory_span(name: str, **kwargs: Any) -> Iterator[Span]:
    span = start_factory_span(name, **kwargs)
    try:
        yield span
    except Exception as exc:  # noqa: BLE001 — record then re-raise
        span.set_status(Status(StatusCode.ERROR, str(exc)))
        span.record_exception(exc)
        raise
    finally:
        span.end()
        # Kind OSS demo: flush promptly so Jaeger UI updates without waiting for batch timer.
        try:
            provider = trace.get_tracer_provider()
            force_flush = getattr(provider, "force_flush", None)
            if callable(force_flush):
                force_flush(timeout_millis=3000)
        except Exception:  # noqa: BLE001
            pass
