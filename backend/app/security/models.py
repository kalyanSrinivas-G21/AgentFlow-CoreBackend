# backend/app/security/models.py
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
import uuid

# Graceful fallback if app.db Base isn't globally exposed yet
try:
    from app.db import Base
except ImportError:
    from sqlalchemy.orm import declarative_base
    Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)

class ProjectMember(Base):
    __tablename__ = "project_members"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    role = Column(String, default="member")