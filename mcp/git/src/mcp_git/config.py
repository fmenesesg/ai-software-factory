"""Git MCP configuration from bootstrap env."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class GitMcpSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    workspace_root: str = Field(default=".", validation_alias="WORKSPACE_ROOT")
    github_owner: str = Field(default="fmenesesg", validation_alias="GITHUB_OWNER")
    github_repo: str = Field(default="asf-demo-app", validation_alias="GITHUB_REPO")
    allowed_remote: str | None = Field(
        default=None,
        validation_alias="GIT_ALLOWED_REMOTE",
        description="Exact remote URL allowed for push; defaults to github.com/{owner}/{repo}.git",
    )
    dry_run: bool = Field(default=False, validation_alias="DRY_RUN")
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8093)

    def resolved_allowed_remote(self) -> str:
        if self.allowed_remote and self.allowed_remote.strip():
            return self.allowed_remote.strip()
        return f"https://github.com/{self.github_owner}/{self.github_repo}.git"
