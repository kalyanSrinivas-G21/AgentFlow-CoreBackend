# backend/app/db.py
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

# Use environment variable matching Docker Compose, eliminating localhost fallback
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://admin:password@db:5432/sovereign_ai"
)

# Create the async engine
engine = create_async_engine(DATABASE_URL, echo=True, poolclass=NullPool)

# Create a session factory for your API to interact with the DB
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

# This is the 'Base' that Alembic is looking for!
class Base(DeclarativeBase):
    pass

# Dependency to get database sessions in your FastAPI routes
async def get_db():
    async with async_session_maker() as session:
        yield session