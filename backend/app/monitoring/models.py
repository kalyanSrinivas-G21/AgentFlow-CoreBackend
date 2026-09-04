# backend/app/monitoring/models.py
import uuid
from sqlalchemy import Column, Float, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db import Base

class ResourceMetric(Base):
    """Stores a snapshot of system resource utilization."""
    __tablename__ = "resource_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cpu_percent = Column(Float, nullable=False)
    memory_percent = Column(Float, nullable=False)
    gpu_percent = Column(Float, nullable=True)
    active_tasks = Column(Integer, nullable=False, default=0)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())