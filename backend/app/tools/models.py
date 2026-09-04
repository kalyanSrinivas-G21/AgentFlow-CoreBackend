# backend/app/tools/models.py
import uuid
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db import Base

class ToolExecution(Base):
    __tablename__ = "tool_executions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_step_id = Column(UUID(as_uuid=True), ForeignKey("plan_steps.id", ondelete="RESTRICT"), nullable=False)
    tool_name = Column(String, nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, nullable=False)
    duration_ms = Column(Integer, nullable=True)
    error_message = Column(String, nullable=True)