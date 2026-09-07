# backend/app/tools/models.py
import uuid
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone

class ToolResult(BaseModel):
    """Canonical standardized output for all tool executions."""
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    duration_ms: float = 0.0
    executed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# SQLAlchemy ORM Model representation for the DB
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.db import Base

class ToolExecution(Base):
    __tablename__ = 'tool_executions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_step_id = Column(UUID(as_uuid=True), ForeignKey('plan_steps.id', ondelete='CASCADE'), nullable=False)
    status = Column(String, nullable=False) # COMPLETED, FAILED
    result = Column(JSONB, nullable=True) # Serialized ToolResult
    executed_at = Column(DateTime(timezone=True), server_default=func.now())