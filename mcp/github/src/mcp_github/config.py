"""GitHub MCP configuration."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class GitHubMcpSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    github_token: str | None = Field(default=None, validation_alias="GITHUB_TOKEN")
    github_owner: str = Field(default="fmenesesg", validation_alias="GITHUB_OWNER")
    github_repo: str = Field(default="ai-software-factory", validation_alias="GITHUB_REPO")
    api_base: str = Field(default="https://api.github.com", validation_alias="GITHUB_API_BASE")
    dry_run: bool = Field(default=False, validation_alias="DRY_RUN")
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8091)
