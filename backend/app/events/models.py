# backend/app/events/models.py
import uuid
from sqlalchemy import Column, String, DateTime, Integer, Index, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.db import Base

class EventRecord(Base):
    __tablename__ = "event_records"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String, nullable=False)
    occurred_at = Column(DateTime(timezone=True), server_default=func.now())
    source = Column(String, nullable=False)
    task_id = Column(UUID(as_uuid=True), nullable=True)
    agent_run_id = Column(UUID(as_uuid=True), nullable=True)
    correlation_id = Column(UUID(as_uuid=True), nullable=False)
    causation_id = Column(UUID(as_uuid=True), nullable=True)
    payload = Column(JSONB, nullable=False)
    schema_version = Column(Integer, nullable=False, default=1)

    __table_args__ = (
        Index("ix_event_records_task_id", "task_id"),
        Index("ix_event_records_event_type", "event_type"),
        Index("ix_event_records_occurred_at", "occurred_at"),
    )

class OutboxEvent(Base):
    """Transactional Outbox table for reliable Redis event delivery."""
    __tablename__ = "outbox_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stream_name = Column(String, nullable=False)
    event_payload = Column(String, nullable=False)
    idempotency_key = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed = Column(Boolean, nullable=False, default=False)
    
    __table_args__ = (
        Index("ix_outbox_events_processed", "processed"),
    )