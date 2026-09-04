# backend/app/agents/orchestrator.py (MODIFIED)
import logging
from app.tasks.models import AgentRun, PlanStep
from app.events.publisher import publish
from app.events.envelope import EventEnvelope
from app.agents.planner import Planner
from app.agents.executor import Executor
from app.agents.validator import Validator

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    def __init__(self, db_session, redis_client):
        self.db = db_session
        self.redis = redis_client
        self.planner = Planner()
        self.executor = Executor(self.db, self.redis)
        self.validator = Validator(self.db)  # <-- MODIFIED: Passed DB session to Validator

    async def run(self, task) -> dict:
        """Main agentic loop: Plan -> Execute -> Validate -> (Complete | Retry | Fail)"""
        logger.info(f"Starting Agent Orchestrator for Task {task.id}")

        agent_run = AgentRun(task_id=task.id, status="RUNNING")
        self.db.add(agent_run)
        
        run_started_evt = EventEnvelope(
            event_type="agent.run.started",
            source="agent_orchestrator",
            task_id=task.id,
            correlation_id=task.id,
            payload={"status": "RUNNING"}
        )
        await publish(self.db, self.redis, run_started_evt)
        await self.db.commit()
        await self.db.refresh(agent_run)

        max_retries = 1
        max_total_steps = 6
        steps_executed = 0
        prior_failure = None

        try:
            prompt = str(task.input_payload.get("prompt", task.input_payload) if isinstance(task.input_payload, dict) else task.input_payload)

            for attempt in range(max_retries + 1):
                logger.info(f"Agent Loop Attempt {attempt + 1}")

                await self.db.refresh(task)
                if task.status in ("CANCEL_REQUESTED", "CANCELLED"):
                    agent_run.status = "CANCELLED"
                    await self.db.commit()
                    return {"error": "Task was cancelled by user."}

                draft_steps = await self.planner.plan(prompt, prior_failure)
                
                plan_created_evt = EventEnvelope(
                    event_type="agent.plan.created",
                    source="agent_orchestrator",
                    task_id=task.id,
                    correlation_id=agent_run.id,
                    payload={"step_count": len(draft_steps), "attempt": attempt + 1}
                )
                await publish(self.db, self.redis, plan_created_evt)
                await self.db.commit()

                for draft in draft_steps:
                    if steps_executed >= max_total_steps:
                        logger.warning(f"Iteration cap ({max_total_steps}) reached.")
                        break

                    plan_step = PlanStep(
                        agent_run_id=agent_run.id,
                        step_number=steps_executed + 1,
                        tool_name=draft.tool_name,
                        tool_args=draft.args,
                        reason=draft.reason,
                        status="QUEUED"
                    )
                    self.db.add(plan_step)
                    await self.db.commit()
                    await self.db.refresh(plan_step)

                    await self.executor.execute_step(plan_step, task.id)
                    steps_executed += 1

                val_started_evt = EventEnvelope(
                    event_type="validation.started",
                    source="agent_validator",
                    task_id=task.id,
                    correlation_id=agent_run.id,
                    payload={}
                )
                await publish(self.db, self.redis, val_started_evt)
                await self.db.commit()

                validation_result = await self.validator.validate(agent_run, task) # <-- MODIFIED: Passing task object directly

                if validation_result.passed:
                    val_passed_evt = EventEnvelope(
                        event_type="validation.passed",
                        source="agent_validator",
                        task_id=task.id,
                        correlation_id=agent_run.id,
                        payload={"reason": validation_result.reason}
                    )
                    await publish(self.db, self.redis, val_passed_evt)
                    
                    agent_run.status = "COMPLETED"
                    run_completed_evt = EventEnvelope(
                        event_type="agent.run.completed",
                        source="agent_orchestrator",
                        task_id=task.id,
                        correlation_id=agent_run.id,
                        payload={"status": "COMPLETED"}
                    )
                    await publish(self.db, self.redis, run_completed_evt)
                    await self.db.commit()
                    return {"status": "success", "steps_executed": steps_executed}
                else:
                    logger.warning(f"Validation failed: {validation_result.reason}")
                    prior_failure = validation_result.reason

            logger.error("Agent run failed to pass validation within retry limits.")
            agent_run.status = "FAILED"
            run_failed_evt = EventEnvelope(
                event_type="agent.run.failed",
                source="agent_orchestrator",
                task_id=task.id,
                correlation_id=agent_run.id,
                payload={"error": "Max retries exceeded", "last_failure": prior_failure}
            )
            await publish(self.db, self.redis, run_failed_evt)
            await self.db.commit()
            return {"error": "Validation failed after max retries", "reason": prior_failure}

        except Exception as e:
            logger.exception("Fatal error in agent loop.")
            await self.db.rollback()
            agent_run.status = "FAILED"
            run_failed_evt = EventEnvelope(
                event_type="agent.run.failed",
                source="agent_orchestrator",
                task_id=task.id,
                correlation_id=agent_run.id,
                payload={"error": str(e)}
            )
            await publish(self.db, self.redis, run_failed_evt)
            await self.db.commit()
            raise