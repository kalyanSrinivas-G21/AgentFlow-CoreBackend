# backend/app/tasks/repository.py
from uuid import UUID
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.tasks.models import Task, Project

class TaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_project(self, project_id: UUID) -> Optional[Project]:
        result = await self.session.execute(select(Project).where(Project.id == project_id))
        return result.scalar_one_or_none()

    async def get_task(self, task_id: UUID) -> Optional[Task]:
        result = await self.session.execute(select(Task).where(Task.id == task_id))
        return result.scalar_one_or_none()

    async def list_tasks_by_project(self, project_id: UUID) -> List[Task]:
        result = await self.session.execute(select(Task).where(Task.project_id == project_id))
        return list(result.scalars().all())

    async def create_task(self, task: Task) -> Task:
        self.session.add(task)
        await self.session.flush()
        return task

    async def update_task_status(self, task: Task, new_status: str) -> Task:
        task.status = new_status
        await self.session.flush()
        return task