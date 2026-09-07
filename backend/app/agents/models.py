# backend/app/agents/models.py
import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.db import Base

class AgentRun(Base):
    __tablename__ = 'agent_runs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False)
    status = Column(String, nullable=False, default="RUNNING")
    tier_used = Column(Integer, nullable=True)  # RECONCILED: Made nullable
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    failure_reason = Column(String, nullable=True)

class PlanStep(Base):
    __tablename__ = 'plan_steps'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_run_id = Column(UUID(as_uuid=True), ForeignKey('agent_runs.id', ondelete='CASCADE'), nullable=False)
    
    step_number = Column(Integer, nullable=False)  # RECONCILED: Enforced step_number instead of step_index
    tool_name = Column(String, nullable=False)
    tool_args = Column(JSONB, nullable=False)      # RECONCILED: Enforced tool_args instead of args
    
    status = Column(String, nullable=False, default="PENDING")
    retryable = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())