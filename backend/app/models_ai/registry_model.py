# backend/app/models_ai/registry_model.py
import uuid
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.db import Base

class ModelRegistryEntry(Base):
    __tablename__ = "model_registry"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id = Column(String, nullable=False, unique=True, index=True)
    display_name = Column(String, nullable=False)
    provider_type = Column(String, nullable=False)
    runtime_type = Column(String, nullable=False)
    location = Column(String, nullable=False)
    capabilities = Column(JSONB, nullable=False, default=list)
    modalities = Column(JSONB, nullable=False, default=list)
    context_limit = Column(Integer, nullable=True)
    estimated_vram_mb = Column(Integer, nullable=True)
    measured_vram_mb = Column(Integer, nullable=True)
    cpu_fallback = Column(Boolean, nullable=False, default=False)
    gpu_required = Column(Boolean, nullable=False, default=False)
    supported_devices = Column(JSONB, nullable=False, default=list)
    version = Column(String, nullable=True)
    configuration = Column(JSONB, nullable=False, default=dict)
    availability = Column(Boolean, nullable=False, default=False)
    load_state = Column(String, nullable=False, default="unloaded")
    health = Column(String, nullable=False, default="unavailable")
    failure_reason = Column(String, nullable=True)
    last_checked_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())