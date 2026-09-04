# backend/app/agents/executor.py
import logging
import asyncio
from app.tasks.models import ToolExecution
from app.tasks.repository import TaskRepository
from app.events.publisher import publish
from app.events.envelope import EventEnvelope
from app.tools.policy import PolicyEngine
from app.tools.base import TOOL_REGISTRY
from app.workspace.service import SecurityError
from app.security.audit import log_action_sync

logger = logging.getLogger(__name__)

class Executor:
    def __init__(self, db_session, redis_client):
        self.db = db_session
        self.redis = redis_client
        self.repo = TaskRepository(self.db)

    async def execute_step(self, plan_step, task_id) -> str:
        logger.info(f"Executing step {plan_step.step_number}: {plan_step.tool_name}")
        
        task = await self.repo.get_task(task_id)
        if not task:
            return await self._fail_execution(plan_step, task_id, "Parent task not found.")

        # 1. State Transition: Step Started
        plan_step.status = "RUNNING"
        step_started_evt = EventEnvelope(
            event_type="agent.step.started",
            source="agent_executor",
            task_id=task_id,
            correlation_id=plan_step.id,
            payload={"step_number": plan_step.step_number, "tool": plan_step.tool_name}
        )
        await publish(self.db, self.redis, step_started_evt)
        await self.db.commit()

        tool_started_evt = EventEnvelope(
            event_type="tool.execution.started",
            source="agent_executor",
            task_id=task_id,
            correlation_id=plan_step.id,
            payload={"tool": plan_step.tool_name, "args": plan_step.tool_args}
        )
        await publish(self.db, self.redis, tool_started_evt)
        await self.db.commit()

        # 2. Policy Interception
        decision = PolicyEngine.check(plan_step.tool_name, plan_step.tool_args, task.project_id)
        
        if not decision.allowed:
            # Audit denied execution
            log_action_sync(self.db, actor="agent", action="tool_execution_denied", target_type="tool", target_id=plan_step.tool_name, details={"args": plan_step.tool_args, "reason": decision.reason})
            await self.db.commit()
            return await self._fail_execution(plan_step, task_id, f"policy_denied: {decision.reason}")

        # Audit allowed execution intent
        log_action_sync(self.db, actor="agent", action="tool_execution_started", target_type="tool", target_id=plan_step.tool_name, details={"args": plan_step.tool_args})
        await self.db.commit()

        # 3. Tool Execution with Isolation and Timeouts
        tool = TOOL_REGISTRY[plan_step.tool_name]
        try:
            result = await asyncio.wait_for(
                tool.run(plan_step.tool_args, str(task.project_id), db=self.db),
                timeout=tool.timeout_s
            )
            final_result_str = str(result)
            
        except asyncio.TimeoutError:
            return await self._fail_execution(plan_step, task_id, "timeout")
        except SecurityError as e:
            return await self._fail_execution(plan_step, task_id, f"security_violation: {str(e)}")
        except Exception as e:
            logger.exception("Error executing tool")
            return await self._fail_execution(plan_step, task_id, f"execution_error: {str(e)}")

        # 4. Success Commit
        execution_record = ToolExecution(
            plan_step_id=plan_step.id,
            status="COMPLETED",
            result=final_result_str
        )
        self.db.add(execution_record)
        
        log_action_sync(self.db, actor="agent", action="tool_execution_completed", target_type="tool", target_id=plan_step.tool_name, details={"status": "success"})

        tool_completed_evt = EventEnvelope(
            event_type="tool.execution.completed",
            source="agent_executor",
            task_id=task_id,
            correlation_id=plan_step.id,
            payload={"tool": plan_step.tool_name, "result": final_result_str}
        )
        await publish(self.db, self.redis, tool_completed_evt)

        plan_step.status = "COMPLETED"
        step_completed_evt = EventEnvelope(
            event_type="agent.step.completed",
            source="agent_executor",
            task_id=task_id,
            correlation_id=plan_step.id,
            payload={"step_number": plan_step.step_number, "status": "COMPLETED"}
        )
        await publish(self.db, self.redis, step_completed_evt)
        await self.db.commit()

        return final_result_str

    async def _fail_execution(self, plan_step, task_id, reason: str) -> str:
        logger.error(f"Tool execution failed for {plan_step.tool_name}: {reason}")
        
        execution_record = ToolExecution(
            plan_step_id=plan_step.id,
            status="FAILED",
            result=reason
        )
        self.db.add(execution_record)
        
        log_action_sync(self.db, actor="agent", action="tool_execution_failed", target_type="tool", target_id=plan_step.tool_name, details={"reason": reason})
        
        tool_failed_evt = EventEnvelope(
            event_type="tool.execution.failed",
            source="agent_executor",
            task_id=task_id,
            correlation_id=plan_step.id,
            payload={"tool": plan_step.tool_name, "reason": reason}
        )
        await publish(self.db, self.redis, tool_failed_evt)
        
        plan_step.status = "FAILED"
        step_failed_evt = EventEnvelope(
            event_type="agent.step.failed",
            source="agent_executor",
            task_id=task_id,
            correlation_id=plan_step.id,
            payload={"step_number": plan_step.step_number, "status": "FAILED", "reason": reason}
        )
        await publish(self.db, self.redis, step_failed_evt)
        await self.db.commit()
        
        return reason