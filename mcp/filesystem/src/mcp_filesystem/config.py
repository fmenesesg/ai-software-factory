"""Filesystem MCP configuration."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class FilesystemMcpSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    workspace_root: str = Field(default=".", validation_alias="WORKSPACE_ROOT")
    # Comma-separated relative roots allowed for writes (under workspace_root).
    writable_roots: str = Field(
        default="sample-app,docs/architecture,agents,mcp,packages,platform,scripts",
        validation_alias="FS_WRITABLE_ROOTS",
    )
    # Docs-like names (requirements.txt, README.sh, *.mdx) only under these roots.
    docs_like_roots: str = Field(
        default="docs,sample-app",
        validation_alias="FS_DOCS_LIKE_ROOTS",
    )
    dry_run: bool = Field(default=False, validation_alias="DRY_RUN")
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8092)

    def writable_root_list(self) -> list[str]:
        return [p.strip() for p in self.writable_roots.split(",") if p.strip()]

    def docs_like_root_list(self) -> list[str]:
        return [p.strip() for p in self.docs_like_roots.split(",") if p.strip()]
