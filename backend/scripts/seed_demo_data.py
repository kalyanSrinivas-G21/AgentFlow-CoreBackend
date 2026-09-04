# backend/scripts/seed_demo_data.py
import asyncio
import logging
from uuid import UUID
from sqlalchemy import select
from app.db import async_session_maker
from app.tasks.models import Project

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Hardcoded UUID for frontend predictability
DEMO_PROJECT_ID = UUID("123e4567-e89b-12d3-a456-426614174000")

async def seed_data():
    async with async_session_maker() as session:
        # Check if project already exists (idempotent)
        result = await session.execute(select(Project).where(Project.id == DEMO_PROJECT_ID))
        existing_project = result.scalar_one_or_none()
        
        if existing_project:
            logger.info(f"✅ Demo project already exists: {existing_project.name} ({existing_project.id})")
            return

        demo_project = Project(
            id=DEMO_PROJECT_ID,
            name="SIH 2026 Core Demonstration"
        )
        session.add(demo_project)
        await session.commit()
        logger.info(f"🎉 Successfully seeded Demo Project: {demo_project.name} ({demo_project.id})")

if __name__ == "__main__":
    asyncio.run(seed_data())