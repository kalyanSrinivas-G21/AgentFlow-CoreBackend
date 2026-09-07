# backend/app/agents/executor.py
import logging
import asyncio
import time
from pydantic import ValidationError
from app.tools.models import ToolExecution, ToolResult
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

    async def execute_step(self, plan_step, task_id) -> ToolResult:
        logger.info(f"Executing step {plan_step.step_number}: {plan_step.tool_name}")
        
        task = await self.repo.get_task(task_id)
        if not task:
            return await self._fail_execution(plan_step, task_id, "Parent task not found.")

        plan_step.status = "RUNNING"
        await self._emit_event("agent.step.started", task_id, plan_step.id, {"step_number": plan_step.step_number, "tool": plan_step.tool_name})
        await self._emit_event("tool.execution.started", task_id, plan_step.id, {"tool": plan_step.tool_name, "args": plan_step.tool_args})

        # ==========================================
        # STAGE 1: Tool Exists Verification
        # ==========================================
        if plan_step.tool_name not in TOOL_REGISTRY:
            return await self._fail_execution(plan_step, task_id, f"registry_error: Tool '{plan_step.tool_name}' is not registered.")
        
        tool = TOOL_REGISTRY[plan_step.tool_name]

        # ==========================================
        # STAGE 2: Permission & Policy Check
        # ==========================================
        decision = PolicyEngine.check(plan_step.tool_name, plan_step.tool_args, task.project_id)
        if not decision.allowed:
            log_action_sync(self.db, actor="agent", action="tool_execution_denied", target_type="tool", target_id=plan_step.tool_name, details={"args": plan_step.tool_args, "reason": decision.reason})
            await self.db.commit()
            return await self._fail_execution(plan_step, task_id, f"policy_denied: {decision.reason}")

        # ==========================================
        # STAGE 3: Pydantic Schema Validation
        # ==========================================
        try:
            # Validate LLM arguments strictly before passing to tool code
            validated_args = tool.input_schema(**plan_step.tool_args).model_dump()
        except ValidationError as e:
            return await self._fail_execution(plan_step, task_id, f"schema_validation_error: {e.errors()}")

        log_action_sync(self.db, actor="agent", action="tool_execution_started", target_type="tool", target_id=plan_step.tool_name, details={"args": validated_args})
        await self.db.commit()

        # ==========================================
        # STAGE 4: Safe Execution
        # ==========================================
        start_time = time.perf_counter()
        try:
            result: ToolResult = await asyncio.wait_for(
                tool.run(validated_args, str(task.project_id), db=self.db),
                timeout=tool.timeout_s
            )
        except asyncio.TimeoutError:
            return await self._fail_execution(plan_step, task_id, "timeout")
        except SecurityError as e:
            return await self._fail_execution(plan_step, task_id, f"security_violation: {str(e)}")
        except Exception as e:
            logger.exception("Error executing tool")
            return await self._fail_execution(plan_step, task_id, f"execution_error: {str(e)}")
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000

        # Post-Execution Standardization
        if not isinstance(result, ToolResult):
            result = ToolResult(success=True, output=str(result))
            
        result.duration_ms = duration_ms

        execution_record = ToolExecution(
            plan_step_id=plan_step.id,
            status="COMPLETED",
            result=result.model_dump(mode='json')
        )
        self.db.add(execution_record)
        log_action_sync(self.db, actor="agent", action="tool_execution_completed", target_type="tool", target_id=plan_step.tool_name, details={"status": "success"})

        await self._emit_event("tool.execution.completed", task_id, plan_step.id, {"tool": plan_step.tool_name, "result": result.model_dump(mode='json')})
        
        plan_step.status = "COMPLETED"
        await self._emit_event("agent.step.completed", task_id, plan_step.id, {"step_number": plan_step.step_number, "status": "COMPLETED"})

        return result

    async def _fail_execution(self, plan_step, task_id, reason: str) -> ToolResult:
        logger.error(f"Tool execution failed for {plan_step.tool_name}: {reason}")
        
        failed_result = ToolResult(success=False, error=reason)
        
        execution_record = ToolExecution(
            plan_step_id=plan_step.id,
            status="FAILED",
            result=failed_result.model_dump(mode='json')
        )
        self.db.add(execution_record)
        
        log_action_sync(self.db, actor="agent", action="tool_execution_failed", target_type="tool", target_id=plan_step.tool_name, details={"reason": reason})
        
        await self._emit_event("tool.execution.failed", task_id, plan_step.id, {"tool": plan_step.tool_name, "reason": reason})
        
        plan_step.status = "FAILED"
        await self._emit_event("agent.step.failed", task_id, plan_step.id, {"step_number": plan_step.step_number, "status": "FAILED", "reason": reason})
        
        return failed_result

    async def _emit_event(self, event_type, task_id, correlation_id, payload):
        evt = EventEnvelope(
            event_type=event_type,
            source="agent_executor",
            task_id=task_id,
            correlation_id=correlation_id,
            payload=payload
        )
        await publish(self.db, self.redis, evt)
        await self.db.commit()