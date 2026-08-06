"""Gateway configuration from environment / bootstrap session."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewaySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )

    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8081)
    upstream_url: str = Field(
        default="http://127.0.0.1:9",
        validation_alias="OSAI_INFERENCE_URL",
        description="Live OSAI/Granite base URL (wired live in M2; stub path OK in M1).",
    )
    upstream_model: str = Field(
        default="ibm/granite-*-instruct",
        validation_alias="OSAI_MODEL_ID",
    )
    upstream_api_key: str | None = Field(default=None, validation_alias="OSAI_API_KEY")
    timeout_seconds: float = Field(default=60.0, validation_alias="GATEWAY_TIMEOUT_SECONDS")
    max_retries: int = Field(default=2, validation_alias="GATEWAY_MAX_RETRIES")
    stub_mode: bool = Field(
        default=True,
        validation_alias="GATEWAY_STUB_MODE",
        description="When true, /v1/chat/completions returns a local stub without upstream.",
    )
    inference_fallback: bool = Field(default=False, validation_alias="INFERENCE_FALLBACK")
