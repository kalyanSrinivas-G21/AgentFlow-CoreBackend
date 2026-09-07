# backend/app/tasks/models.py
import uuid
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.db import Base

class Project(Base):
    __tablename__ = 'projects'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Task(Base):
    __tablename__ = 'tasks'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    task_type = Column(String, nullable=False)
    status = Column(String, nullable=False, default="QUEUED")
    input_payload = Column(JSONB, nullable=False)
    result_payload = Column(JSONB, nullable=True)
    retry_of_task_id = Column(UUID(as_uuid=True), ForeignKey('tasks.id', ondelete='SET NULL'), nullable=True)
    
    # Worker Lease Fields
    worker_id = Column(String, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    heartbeat = Column(DateTime(timezone=True), nullable=True)
    lease_expiry = Column(DateTime(timezone=True), nullable=True)
    attempt_count = Column(Integer, nullable=False, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())