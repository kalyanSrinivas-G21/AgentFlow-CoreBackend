# backend/app/tasks/runner.py (MODIFIED)
import logging
import os
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.tasks.repository import TaskRepository
from app.events.publisher import publish
from app.events.envelope import EventEnvelope
from app.models_ai.tier_router import TierRouter
from app.models_ai.ollama_provider import OllamaProvider
from app.agents.orchestrator import AgentOrchestrator

logger = logging.getLogger(__name__)

class TaskRunner:
    def __init__(self, db_session: AsyncSession, redis_client: Redis):
        self.db = db_session
        self.redis = redis_client
        self.repo = TaskRepository(db_session)
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")

    async def run(self, task_id: UUID) -> None:
        task = await self.repo.get_task(task_id)
        if not task:
            logger.error(f"Task {task_id} not found.")
            return

        if task.status not in ("QUEUED", "RUNNING"):
            logger.warning(f"Task {task_id} is in status {task.status}. Skipping run.")
            return

        # 1. State Transition: RUNNING
        task = await self.repo.update_task_status(task, "RUNNING")
        running_evt = EventEnvelope(
            event_type="task.started",
            source="task_runner",
            task_id=task.id,
            correlation_id=task.id,
            payload={"status": "RUNNING"}
        )
        await publish(self.db, self.redis, running_evt)
        await self.db.commit()
        await self.db.refresh(task)

        try:
            # ==========================================
            # 2. Branch: Agentic Workflow vs Direct LLM
            # ==========================================
            if task.task_type == "agentic_workflow":
                logger.info(f"Delegating Task {task_id} to Agent Orchestrator.")
                orchestrator = AgentOrchestrator(self.db, self.redis)
                final_result = await orchestrator.run(task)
                
                if "error" in final_result:
                    raise Exception(final_result["error"])
                task.result_payload = final_result

            else:
                logger.info(f"Executing standard Task {task_id} with direct LLM call.")
                tier_router = TierRouter()
                model_name = tier_router.get_model_for_tier(1)
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

            # 3. State Transition: COMPLETED
            task = await self.repo.update_task_status(task, "COMPLETED")
            completed_evt = EventEnvelope(
                event_type="task.completed",
                source="task_runner",
                task_id=task.id,
                correlation_id=task.id,
                payload={"status": "COMPLETED", "result": task.result_payload}
            )
            await publish(self.db, self.redis, completed_evt)
            await self.db.commit()

        except Exception as e:
            logger.exception(f"Task {task_id} FAILED: {e}")
            await self.db.rollback()
            task = await self.repo.get_task(task_id)
            
            task.result_payload = {"error": str(e)}
            task = await self.repo.update_task_status(task, "FAILED")
            
            failed_evt = EventEnvelope(
                event_type="task.failed",
                source="task_runner",
                task_id=task.id,
                correlation_id=task.id,
                payload={"status": "FAILED", "error": str(e)}
            )
            await publish(self.db, self.redis, failed_evt)
            await self.db.commit()