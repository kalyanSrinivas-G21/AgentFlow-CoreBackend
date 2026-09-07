# backend/tests/conftest.py
import pytest_asyncio
import os
import jwt
from uuid import uuid4
import datetime
from app.db import async_session_maker, engine, Base

import app.security.models
import app.tasks.models
import app.agents.models
import app.tools.models
import app.events.models
import app.workspace.models
import app.monitoring.models

@pytest_asyncio.fixture(autouse=True)
async def prepare_integration_db():
    async with engine.begin() as conn:
        await conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
        await conn.run_sync(Base.metadata.create_all)
        
    yield
    await engine.dispose()

@pytest_asyncio.fixture
async def auth_context():
    """
    Creates a real user, project, and project_member in the PostgreSQL database.
    Signs a legitimate JWT token for cross-service API requests.
    """
    user_id = uuid4()
    project_id = uuid4()
    
    async with async_session_maker() as db:
        # Create Project first to satisfy Foreign Keys and TaskService checks
        project = app.tasks.models.Project(
            id=project_id, 
            name="Integration Test Project",
            created_at=datetime.datetime.now(datetime.timezone.utc),
            updated_at=datetime.datetime.now(datetime.timezone.utc)
        )
        user = app.security.models.User(id=user_id, username=f"test_{user_id.hex[:8]}", hashed_password="fake")
        member = app.security.models.ProjectMember(project_id=project_id, user_id=user_id, role="admin")
        
        db.add(project)
        db.add(user)
        db.add(member)
        await db.commit()
        
    secret = os.getenv("JWT_SECRET", "super-secret-key-change-in-prod")
    token = jwt.encode({"sub": str(user_id), "username": user.username}, secret, algorithm="HS256")
    
    return {"project_id": str(project_id), "token": token, "user_id": str(user_id)}