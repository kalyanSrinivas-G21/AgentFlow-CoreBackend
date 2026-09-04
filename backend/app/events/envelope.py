from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

class EventEnvelope(BaseModel):
    """
    Standard event shape for the sovereign AI workbench.
    """
    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str
    task_id: Optional[UUID] = None
    agent_run_id: Optional[UUID] = None
    correlation_id: UUID
    causation_id: Optional[UUID] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    schema_version: int = 1

    @property
    def stream_name(self) -> str:
        """Derive the Redis stream name from the event_type prefix."""
        prefix = self.event_type.split(".")[0]
        return f"stream:{prefix}"
        
    @property
    def idempotency_key(self) -> str:
        """Derive an idempotency key from task/run identity and event type."""
        identity = self.task_id or self.agent_run_id or self.event_id
        return f"{self.event_type}:{identity}:{self.event_id}"