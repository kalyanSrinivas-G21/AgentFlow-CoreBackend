# backend/app/tasks/router.py
from uuid import UUID
from typing import List, AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.tasks.schemas import TaskCreateRequest, TaskResponse
from app.tasks.service import TaskService
from app.db import async_session_maker

router = APIRouter(tags=["tasks"])

# Dependency placeholders - map these to your specific Stage 1/2 connection pools
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session

async def get_redis() -> AsyncGenerator[Redis, None]:
    client = Redis(host='localhost', port=6379, db=0, decode_responses=True)
    try:
        yield client
    finally:
        await client.aclose()

@router.post("/projects/{project_id}/tasks", response_model=TaskResponse, status_code=201)
async def create_task(
    project_id: UUID, 
    req: TaskCreateRequest, 
    db: AsyncSession = Depends(get_db), 
    redis: Redis = Depends(get_redis)
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
    redis: Redis = Depends(get_redis)
):
    svc = TaskService(db, redis)
    task = await svc.get_task(id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.get("/projects/{project_id}/tasks", response_model=List[TaskResponse])
async def list_tasks(
    project_id: UUID, 
    db: AsyncSession = Depends(get_db), 
    redis: Redis = Depends(get_redis)
):
    svc = TaskService(db, redis)
    return await svc.list_tasks(project_id)

@router.post("/tasks/{id}/cancel", response_model=TaskResponse)
async def cancel_task(
    id: UUID, 
    db: AsyncSession = Depends(get_db), 
    redis: Redis = Depends(get_redis)
):
    svc = TaskService(db, redis)
    try:
        task = await svc.cancel_task(id)
        return task
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/tasks/{id}/retry", response_model=TaskResponse, status_code=201)
async def retry_task(
    id: UUID, 
    db: AsyncSession = Depends(get_db), 
    redis: Redis = Depends(get_redis)
):
    svc = TaskService(db, redis)
    try:
        task = await svc.retry_task(id)
        return task
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))