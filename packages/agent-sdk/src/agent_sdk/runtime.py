"""Shared MVP agent invoke request/response contracts."""

from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel, Field


class AgentInvokeRequest(BaseModel):
    run_id: str = Field(default="local-dev")
    artifacts: dict[str, Any] = Field(default_factory=dict)
    input: dict[str, Any] = Field(default_factory=dict)


class AgentInvokeResponse(BaseModel):
    agent: str
    run_id: str
    status: str
    artifacts: dict[str, Any] = Field(default_factory=dict)
    message: str = ""
    usage: dict[str, int] | None = None


def env_gateway_url() -> str:
    return os.environ.get("INFERENCE_GATEWAY_URL", "http://127.0.0.1:8081").rstrip("/")


def env_model_id() -> str:
    return os.environ.get("OSAI_MODEL_ID", "ibm/granite-*-instruct")


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes"}
