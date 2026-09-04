# backend/app/agents/models.py
import uuid
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.db import Base

class AgentRun(Base):
    __tablename__ = "agent_runs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="RESTRICT"), nullable=False)
    tier_used = Column(String, nullable=False)
    iteration_count = Column(Integer, default=0)
    status = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

class PlanStep(Base):
    __tablename__ = "plan_steps"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_run_id = Column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="RESTRICT"), nullable=False)
    step_index = Column(Integer, nullable=False)
    tool_name = Column(String, nullable=False)
    args = Column(JSONB, nullable=False)
    status = Column(String, nullable=False)
    result = Column(JSONB, nullable=True)