# backend/app/tasks/router.py
from uuid import UUID
from typing import List, AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from sqlalchemy import select

from app.tasks.schemas import TaskCreateRequest, TaskResponse
from app.tasks.service import TaskService
from app.tasks.models import Task
from app.db import async_session_maker
from app.security.auth import verify_project_access, get_current_user

router = APIRouter(tags=["tasks"])

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session

async def get_redis() -> AsyncGenerator[Redis, None]:
    client = Redis(host='localhost', port=6379, db=0, decode_responses=True)
    try:
        yield client
    finally:
        await client.aclose()

# RBAC helper for task-specific routes
async def check_task_access(id: UUID, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(Task).where(Task.id == id)
    task_record = (await db.execute(stmt)).scalar_one_or_none()
    if not task_record:
        raise HTTPException(status_code=404, detail="Task not found")
    await verify_project_access(task_record.project_id, user, db)
    return task_record

@router.post("/projects/{project_id}/tasks", response_model=TaskResponse, status_code=201)
async def create_task(
    project_id: UUID, 
    req: TaskCreateRequest, 
    db: AsyncSession = Depends(get_db), 
    redis: Redis = Depends(get_redis),
    user: dict = Depends(verify_project_access) # Step 11.3 RBAC
):
    svc = TaskService(db, redis)
    try:
        task = await svc.create_task(project_id, req)
        return task
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/tasks/{id}", response_model=TaskResponse)
async def get_task(
    id: UUID, 
    db: AsyncSession = Depends(get_db), 
    redis: Redis = Depends(get_redis),
    task_record: Task = Depends(check_task_access) # Step 11.3 RBAC
):
    svc = TaskService(db, redis)
    return await svc.get_task(id)

@router.get("/projects/{project_id}/tasks", response_model=List[TaskResponse])
async def list_tasks(
    project_id: UUID, 
    db: AsyncSession = Depends(get_db), 
    redis: Redis = Depends(get_redis),
    user: dict = Depends(verify_project_access) # Step 11.3 RBAC
):
    svc = TaskService(db, redis)
    return await svc.list_tasks(project_id)

@router.post("/tasks/{id}/cancel", response_model=TaskResponse)
async def cancel_task(
    id: UUID, 
    db: AsyncSession = Depends(get_db), 
    redis: Redis = Depends(get_redis),
    task_record: Task = Depends(check_task_access)
):
    svc = TaskService(db, redis)
    try:
        return await svc.cancel_task(id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/tasks/{id}/retry", response_model=TaskResponse, status_code=201)
async def retry_task(
    id: UUID, 
    db: AsyncSession = Depends(get_db), 
    redis: Redis = Depends(get_redis),
    task_record: Task = Depends(check_task_access)
):
    svc = TaskService(db, redis)
    try:
        return await svc.retry_task(id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))