"""OpenShift MCP configuration."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OpenShiftMcpSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    namespace_prefix: str = Field(default="asf-workshop-", validation_alias="NAMESPACE_PREFIX")
    ocp_api_url: str = Field(default="", validation_alias="OCP_API_URL")
    ocp_token: str = Field(default="", validation_alias="OCP_TOKEN")
    dry_run: bool = Field(default=False, validation_alias="DRY_RUN")
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8094)
