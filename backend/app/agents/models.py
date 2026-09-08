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


class ExecutionTraceRecord(Base):
    __tablename__ = "execution_trace_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    execution_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    step_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    step_type = Column(String, nullable=False)
    component = Column(String, nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    status = Column(String, nullable=False)
    retry_number = Column(Integer, nullable=False, default=0)
    parent_step_id = Column(UUID(as_uuid=True), nullable=True)
    artifact_refs = Column(JSONB, nullable=False, default=list)
    error_category = Column(String, nullable=True)
    safe_summary = Column(String, nullable=True)


class ApprovalRequestRecord(Base):
    __tablename__ = "approval_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    execution_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    operation = Column(String, nullable=False)
    risk_level = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")
    decision_reason = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    decided_at = Column(DateTime(timezone=True), nullable=True)