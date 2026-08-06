"""PostgreSQL checkpoint configuration (same host family as pgvector later)."""

from __future__ import annotations

import os
from typing import Any


def resolve_checkpoint_dsn(
    explicit: str | None = None,
    *,
    environ: dict[str, str] | None = None,
) -> str | None:
    """Resolve checkpoint DSN from explicit arg or bootstrap env (CHECKPOINT_DSN)."""
    env = environ if environ is not None else os.environ
    if explicit is not None and explicit.strip():
        return explicit.strip()
    value = (env.get("CHECKPOINT_DSN") or "").strip()
    return value or None


def build_checkpointer(dsn: str | None = None) -> Any:
    """Return a LangGraph checkpointer.

    - Unset DSN → MemorySaver (local empty-graph boot / unit tests).
    - Set DSN → PostgresSaver backed by a psycopg connection pool.
      Callers that need schema bootstrap should invoke ``checkpointer.setup()``
      once against a reachable database (workshop platform apply, M2+).
    """
    resolved = resolve_checkpoint_dsn(dsn)
    if not resolved:
        from langgraph.checkpoint.memory import MemorySaver

        return MemorySaver()

    from psycopg.rows import dict_row
    from psycopg_pool import ConnectionPool
    from langgraph.checkpoint.postgres import PostgresSaver

    pool = ConnectionPool(
        conninfo=resolved,
        kwargs={
            "autocommit": True,
            "prepare_threshold": 0,
            "row_factory": dict_row,
        },
        open=False,
    )
    pool.open()
    return PostgresSaver(pool)
