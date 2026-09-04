from uuid import UUID
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from app.tasks.models import Task
from app.tasks.schemas import TaskCreateRequest
from app.tasks.repository import TaskRepository
from app.common.exceptions import InvalidTaskStateTransition
from app.events.envelope import EventEnvelope
from app.events.publisher import publish
from app.events import catalog

VALID_STATES = {"CREATED", "QUEUED", "RUNNING", "COMPLETED", "FAILED", "CANCELLED"}
_TASK_QUEUED = getattr(catalog, 'TASK_QUEUED', 'task.queued')
_TASK_CANCEL_REQUESTED = getattr(catalog, 'TASK_CANCEL_REQUESTED', 'task.cancel.requested')

class TaskService:
    def __init__(self, db_session: AsyncSession, redis_client: Redis):
        self.db = db_session
        self.redis = redis_client
        self.repo = TaskRepository(db_session)

    def _enforce_transition(self, current: str, target: str, task_id: UUID):
        if target not in VALID_STATES and target != "CANCEL_REQUESTED":
            raise InvalidTaskStateTransition(current, target, task_id)
        if target in ("CANCELLED", "CANCEL_REQUESTED"):
            if current in ("COMPLETED", "FAILED", "CANCELLED"):
                raise InvalidTaskStateTransition(current, target, task_id)

    async def create_task(self, project_id: UUID, req: TaskCreateRequest) -> Task:
        project = await self.repo.get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        # 1. Database Creation (CREATED)
        task = Task(
            project_id=project_id,
            task_type=req.task_type,
            status="CREATED",
            input_payload=req.input_payload
        )
        task = await self.repo.create_task(task)

        # 2. Publish CREATED Event
        created_evt = EventEnvelope(
            event_type=catalog.TASK_CREATED,
            source="task_service",
            task_id=task.id,
            correlation_id=task.id,
            payload={"task_type": task.task_type, "status": "CREATED"}
        )
        await publish(self.db, self.redis, created_evt)

        # 3. Transition to QUEUED & Publish QUEUED Event
        self._enforce_transition(task.status, "QUEUED", task.id)
        task = await self.repo.update_task_status(task, "QUEUED")
        queued_evt = EventEnvelope(
            event_type=_TASK_QUEUED,
            source="task_service",
            task_id=task.id,
            correlation_id=task.id,
            payload={"task_type": task.task_type, "status": "QUEUED"}
        )
        await publish(self.db, self.redis, queued_evt)
        
        await self.db.commit()
        
        # Async refresh to prevent Pydantic from triggering lazy-loads on expired attributes
        await self.db.refresh(task)
        return task

    async def get_task(self, task_id: UUID) -> Optional[Task]:
        return await self.repo.get_task(task_id)

    async def list_tasks(self, project_id: UUID) -> List[Task]:
        return await self.repo.list_tasks_by_project(project_id)

    async def cancel_task(self, task_id: UUID) -> Task:
        task = await self.repo.get_task(task_id)
        if not task:
            raise ValueError("Task not found")

        self._enforce_transition(task.status, "CANCEL_REQUESTED", task.id)
        
        cancel_evt = EventEnvelope(
            event_type=_TASK_CANCEL_REQUESTED,
            source="task_service",
            task_id=task.id,
            correlation_id=task.id,
            payload={"action": "cancel_requested"}
        )
        await publish(self.db, self.redis, cancel_evt)
        
        if task.status in ("CREATED", "QUEUED"):
            task = await self.repo.update_task_status(task, "CANCELLED")
        
        await self.db.commit()
        
        # Async refresh
        await self.db.refresh(task)
        return task

    async def retry_task(self, task_id: UUID) -> Task:
        old_task = await self.repo.get_task(task_id)
        if not old_task:
            raise ValueError("Task not found")
            
        if old_task.status not in ("FAILED", "CANCELLED", "COMPLETED"):
            raise InvalidTaskStateTransition(old_task.status, "RETRY", task_id)
        
        new_task = Task(
            project_id=old_task.project_id,
            task_type=old_task.task_type,
            status="CREATED",
            input_payload=old_task.input_payload,
            retry_of_task_id=task_id
        )
        new_task = await self.repo.create_task(new_task)

        retry_evt = EventEnvelope(
            event_type=catalog.TASK_CREATED,
            source="task_service",
            task_id=new_task.id,
            correlation_id=new_task.id,
            payload={"task_type": new_task.task_type, "status": "CREATED", "retry_of": str(task_id)}
        )
        await publish(self.db, self.redis, retry_evt)
        
        new_task = await self.repo.update_task_status(new_task, "QUEUED")
        queued_evt = EventEnvelope(
            event_type=_TASK_QUEUED,
            source="task_service",
            task_id=new_task.id,
            correlation_id=new_task.id,
            payload={"task_type": new_task.task_type, "status": "QUEUED"}
        )
        await publish(self.db, self.redis, queued_evt)
        
        await self.db.commit()
        
        # Async refresh
        await self.db.refresh(new_task)
        return new_task