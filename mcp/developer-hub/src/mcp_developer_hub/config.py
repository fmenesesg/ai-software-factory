"""Developer Hub MCP settings (RHDH catalog — not HITL)."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DeveloperHubMcpSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    dry_run: bool = Field(default=True, validation_alias="DRY_RUN")
    rhdh_url: str = Field(default="http://127.0.0.1:7007", validation_alias="RHDH_URL")
    rhdh_token: str | None = Field(default=None, validation_alias="RHDH_TOKEN")
    catalog_entity: str = Field(
        default="component:default/ai-software-factory",
        validation_alias="RHDH_CATALOG_ENTITY",
    )
