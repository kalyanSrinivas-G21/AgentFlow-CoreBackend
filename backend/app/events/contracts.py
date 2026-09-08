from datetime import datetime, timezone
from typing import Any, Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

EventStatus = Literal["queued", "in_progress", "succeeded", "failed", "cancelled"]


class EventEnvelope(BaseModel):
    """Phase 15 realtime envelope; payload contains safe metadata, never chain-of-thought."""

    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    project_id: Optional[UUID] = None
    task_id: Optional[UUID] = None
    execution_id: Optional[UUID] = None
    parent_id: Optional[UUID] = None
    component: str
    status: EventStatus
    payload: dict[str, Any] = Field(default_factory=dict)
    duration_ms: Optional[int] = Field(default=None, ge=0)
    sequence_number: int = Field(ge=0)

    @property
    def stream_name(self) -> str:
        return f"stream:{self.event_type.split('.')[0]}"
