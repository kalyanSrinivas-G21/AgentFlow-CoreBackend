# backend/app/models_ai/registry_model.py
import uuid
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db import Base

class ModelRegistryEntry(Base):
    __tablename__ = "model_registry"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tier = Column(String, nullable=False)
    model_tag = Column(String, nullable=False)
    status = Column(String, nullable=False) # available|unavailable
    last_checked_at = Column(DateTime(timezone=True), server_default=func.now())