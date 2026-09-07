# backend/app/tasks/runner.py
import logging
import os
import datetime
from uuid import UUID
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.tasks.models import Task
from app.tasks.repository import TaskRepository
from app.events.publisher import publish
from app.events.envelope import EventEnvelope
from app.models_ai.router import ModelRouter
from app.models_ai.ollama_provider import OllamaProvider
from app.agents.orchestrator import AgentOrchestrator

logger = logging.getLogger(__name__)

class TaskRunner:
    def __init__(self, db_session: AsyncSession, redis_client: Redis, worker_id: str):
        self.db = db_session
        self.redis = redis_client
        self.repo = TaskRepository(db_session)
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
        self.worker_id = worker_id

    async def run(self, task_id: UUID) -> None:
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        lease_seconds = float(os.getenv("TASK_LEASE_SECONDS", "600"))
        expiry = now + datetime.timedelta(seconds=lease_seconds)
        
        stmt = (
            update(Task)
            .where(Task.id == task_id)
            .where(
                (Task.status == "QUEUED") | 
                ((Task.status == "RUNNING") & (Task.lease_expiry < now))
            )
            .values(
                status="RUNNING",
                worker_id=self.worker_id,
                started_at=now,
                heartbeat=now,
                lease_expiry=expiry,
                attempt_count=Task.attempt_count + 1
            )
            .returning(Task)
        )
        result = await self.db.execute(stmt)
        task = result.scalar_one_or_none()
        
        if not task:
            logger.warning(f"Task {task_id} already claimed, completed, or missing. Skipping duplicate event.")
            return
            
        await self.db.commit()

        running_evt = EventEnvelope(
            event_type="task.started", source="task_runner", task_id=task.id,
            correlation_id=task.id, payload={"status": "RUNNING", "worker_id": self.worker_id}
        )
        await publish(self.db, self.redis, running_evt)
        await self.db.commit()
        await self.db.refresh(task)

        try:
            if task.task_type == "agentic_workflow":
                logger.info(f"Delegating Task {task_id} to Agent Orchestrator.")
                orchestrator = AgentOrchestrator(self.db, self.redis)
                final_result = await orchestrator.run(task)
                
                if "error" in final_result:
                    raise Exception(final_result["error"])
                task.result_payload = final_result

            else:
                logger.info(f"Executing standard Task {task_id} with direct LLM call.")
                router = ModelRouter()
                # Request general capabilities. Allow explicit overrides from payload if present.
                explicit_req = task.input_payload.get("model", "auto") if isinstance(task.input_payload, dict) else "auto"
                model_name = router.route(explicit_model=explicit_req, required_capabilities=["general"])
                
                provider = OllamaProvider(base_url=self.base_url)

                if isinstance(task.input_payload, str):
                    prompt = task.input_payload
                    system = None
                else:
                    prompt = task.input_payload.get("prompt", str(task.input_payload))
                    system = task.input_payload.get("system")

                response_text = await provider.generate(
                    model=model_name, prompt=prompt, system=system
                )
                task.result_payload = {"response": response_text, "model": model_name}

            task.status = "COMPLETED"
            task.worker_id = None
            task.lease_expiry = None
            self.db.add(task)
            
            completed_evt = EventEnvelope(
                event_type="task.completed", source="task_runner", task_id=task.id,
                correlation_id=task.id, payload={"status": "COMPLETED", "result": task.result_payload}
            )
            await publish(self.db, self.redis, completed_evt)
            await self.db.commit()

        except Exception as e:
            logger.exception(f"Task {task_id} FAILED: {e}")
            await self.db.rollback()
            task = await self.repo.get_task(task_id)
            
            task.result_payload = {"error": str(e)}
            task.status = "FAILED"
            task.worker_id = None
            task.lease_expiry = None
            self.db.add(task)
            
            failed_evt = EventEnvelope(
                event_type="task.failed", source="task_runner", task_id=task.id,
                correlation_id=task.id, payload={"status": "FAILED", "error": str(e)}
            )
            await publish(self.db, self.redis, failed_evt)
            await self.db.commit()