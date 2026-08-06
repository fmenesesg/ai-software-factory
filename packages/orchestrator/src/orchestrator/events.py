"""Stage / HITL event types emitted by the orchestrator."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class StageEventType(StrEnum):
    STAGE_ENTERED = "stage.entered"
    STAGE_COMPLETED = "stage.completed"
    HITL_WAITING = "hitl.waiting"
    BOOTSTRAP_COMPLETED = "bootstrap.completed"
    BOOTSTRAP_FAILED = "bootstrap.failed"


class StageEvent(BaseModel):
    type: StageEventType
    run_id: str
    stage: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
