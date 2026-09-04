# backend/app/main.py
import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse

from app.tasks.router import router as tasks_router
from app.common.exceptions import InvalidTaskStateTransition
from app.models_ai.router import router as ai_router
from app.workspace.router import router as workspace_router
from app.realtime.router import router as realtime_router
from app.realtime.manager import consume_redis_streams
from app.security.auth import get_current_actor

# --- NEW MONITORING IMPORTS ---
from app.monitoring.sampler import sample_resources
from app.monitoring.router import router as monitoring_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Startup tasks
    consumer_task = asyncio.create_task(consume_redis_streams(redis_url))
    sampler_task = asyncio.create_task(sample_resources(redis_url))
    
    yield
    
    # Shutdown gracefully
    consumer_task.cancel()
    sampler_task.cancel()

app = FastAPI(title="Sovereign On-Premise Agentic AI Workbench", lifespan=lifespan)

@app.exception_handler(InvalidTaskStateTransition)
async def invalid_state_exception_handler(request: Request, exc: InvalidTaskStateTransition):
    return JSONResponse(
        status_code=400,
        content={"detail": exc.message, "task_id": exc.task_id}
    )

@app.get("/health", tags=["system"])
async def health_check():
    return {"status": "healthy"}

# Apply authentication globally to business routers
secure_dependency = [Depends(get_current_actor)]

app.include_router(tasks_router, prefix="/api/v1", dependencies=secure_dependency)
app.include_router(ai_router, prefix="/api/v1/ai", dependencies=secure_dependency)
app.include_router(workspace_router, dependencies=secure_dependency)
app.include_router(monitoring_router) # The router itself has the dependency

app.include_router(realtime_router)