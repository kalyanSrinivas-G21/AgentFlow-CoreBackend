# backend/app/main.py
import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse

from app.tools.base import init_tools
from app.tasks.router import router as tasks_router
from app.common.exceptions import InvalidTaskStateTransition
from app.models_ai.router import router as ai_router
from app.workspace.router import router as workspace_router
from app.realtime.router import router as realtime_router
from app.realtime.manager import consume_redis_streams
from app.security.auth import get_current_user, validate_local_endpoint

from app.monitoring.sampler import sample_resources
from app.monitoring.router import router as monitoring_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_local_endpoint(os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    
    init_tools()
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # We gracefully handle missing Redis connections when running scripts like export_openapi.py
    consumer_task = None
    sampler_task = None
    if not os.getenv("DISABLE_BACKGROUND_TASKS"):
        consumer_task = asyncio.create_task(consume_redis_streams(redis_url))
        sampler_task = asyncio.create_task(sample_resources(redis_url))
    
    yield
    
    if consumer_task: consumer_task.cancel()
    if sampler_task: sampler_task.cancel()

app = FastAPI(
    title="Sovereign On-Premise Agentic AI Workbench", 
    version="1.0.0",
    description="API Contract for the React Frontend. Includes Task execution, RBAC workspaces, and Local LLM inference.",
    lifespan=lifespan
)

@app.exception_handler(InvalidTaskStateTransition)
async def invalid_state_exception_handler(request: Request, exc: InvalidTaskStateTransition):
    return JSONResponse(status_code=400, content={"detail": exc.message, "task_id": str(exc.task_id)})

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "healthy"}

secure_dependency = [Depends(get_current_user)]

app.include_router(tasks_router, prefix="/api/v1", dependencies=secure_dependency)
app.include_router(ai_router, prefix="/api/v1/ai", dependencies=secure_dependency)
app.include_router(workspace_router, dependencies=secure_dependency)
app.include_router(monitoring_router, tags=["Monitoring"])
app.include_router(realtime_router, tags=["Realtime"])