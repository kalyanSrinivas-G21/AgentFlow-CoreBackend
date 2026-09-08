from abc import ABC, abstractmethod
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

TraceStatus = Literal["queued", "in_progress", "succeeded", "failed", "retrying", "cancelled"]
TraceStepType = Literal[
    "task_started",
    "planning",
    "model_selection",
    "context_retrieval",
    "tool_selection",
    "tool_execution",
    "validation",
    "retry",
    "artifact_generation",
    "approval",
    "task_completed",
]
ErrorCategory = Literal[
    "validation",
    "resource",
    "model",
    "tool",
    "network",
    "security_policy",
    "parser",
    "database",
    "queue",
    "unknown",
]


class ExecutionTraceEvent(BaseModel):
    """Safe execution summary for UI timelines; it intentionally has no reasoning field."""

    event_id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    execution_id: UUID
    step_id: UUID
    step_type: TraceStepType
    component: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[int] = Field(default=None, ge=0)
    status: TraceStatus
    retry_number: int = Field(default=0, ge=0)
    parent_step_id: Optional[UUID] = None
    artifact_refs: list[UUID] = Field(default_factory=list)
    error_category: Optional[ErrorCategory] = None
    safe_summary: Optional[str] = None


class ExecutionTraceSink(ABC):
    """Persistence/publication boundary for structured execution activity."""

    @abstractmethod
    async def append(self, event: ExecutionTraceEvent) -> ExecutionTraceEvent:
        raise NotImplementedError

    @abstractmethod
    async def list_for_execution(self, execution_id: UUID) -> list[ExecutionTraceEvent]:
        raise NotImplementedError
