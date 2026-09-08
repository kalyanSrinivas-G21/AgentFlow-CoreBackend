from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.contracts import ExecutionTraceEvent, ExecutionTraceSink
from app.agents.models import ExecutionTraceRecord


class InMemoryExecutionTraceSink(ExecutionTraceSink):
    """Bounded deterministic trace sink for unit tests and local execution probes."""

    def __init__(self, max_events: int = 512):
        self.max_events = max_events
        self.events: list[ExecutionTraceEvent] = []

    async def append(self, event: ExecutionTraceEvent) -> ExecutionTraceEvent:
        if len(self.events) >= self.max_events:
            self.events.pop(0)
        self.events.append(event)
        return event

    async def list_for_execution(self, execution_id: UUID) -> list[ExecutionTraceEvent]:
        return [event for event in self.events if event.execution_id == execution_id]


class SqlAlchemyExecutionTraceSink(ExecutionTraceSink):
    """Durable PostgreSQL trace sink using metadata-only trace records."""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _to_event(row: ExecutionTraceRecord) -> ExecutionTraceEvent:
        return ExecutionTraceEvent(
            event_id=row.id,
            task_id=row.task_id,
            execution_id=row.execution_id,
            step_id=row.step_id,
            step_type=row.step_type,
            component=row.component,
            start_time=row.start_time,
            end_time=row.end_time,
            duration_ms=row.duration_ms,
            status=row.status,
            retry_number=row.retry_number,
            parent_step_id=row.parent_step_id,
            artifact_refs=row.artifact_refs or [],
            error_category=row.error_category,
            safe_summary=row.safe_summary,
        )

    async def append(self, event: ExecutionTraceEvent) -> ExecutionTraceEvent:
        self.db.add(
            ExecutionTraceRecord(
                id=event.event_id,
                task_id=event.task_id,
                execution_id=event.execution_id,
                step_id=event.step_id,
                step_type=event.step_type,
                component=event.component,
                start_time=event.start_time,
                end_time=event.end_time,
                duration_ms=event.duration_ms,
                status=event.status,
                retry_number=event.retry_number,
                parent_step_id=event.parent_step_id,
                artifact_refs=[str(item) for item in event.artifact_refs],
                error_category=event.error_category,
                safe_summary=event.safe_summary,
            )
        )
        await self.db.flush()
        return event

    async def list_for_execution(self, execution_id: UUID) -> list[ExecutionTraceEvent]:
        rows = list((await self.db.scalars(
            select(ExecutionTraceRecord)
            .where(ExecutionTraceRecord.execution_id == execution_id)
            .order_by(ExecutionTraceRecord.start_time)
        )).all())
        return [self._to_event(row) for row in rows]
