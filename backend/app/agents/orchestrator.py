import logging
import os
from types import SimpleNamespace
from typing import Any, Dict
from uuid import uuid4

from app.agents.approval import InMemoryApprovalGate
from app.agents.graph import AgentState, WorkflowGraph
from app.agents.trace_store import SqlAlchemyExecutionTraceSink
from app.agents.executor import Executor
from app.models_ai.router_v2 import ModelRouter
from app.models_ai.runtime import OllamaRuntime
from app.tasks.models import Task

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Manages a bounded graph run and returns safe execution state."""

    def __init__(self, db_session, redis_client, *, runtime=None, trace_sink=None, approval_gate=None, executor=None):
        self.db = db_session
        self.redis = redis_client
        self.runtime = runtime or OllamaRuntime()
        self.trace_sink = trace_sink or SqlAlchemyExecutionTraceSink(db_session)
        self.approval_gate = approval_gate or InMemoryApprovalGate()
        self.executor = executor or Executor(db_session, redis_client)

    async def run(self, task: Task) -> Dict[str, Any]:
        execution_id = uuid4()
        objective = task.input_payload.get("prompt", "") if isinstance(task.input_payload, dict) else str(task.input_payload)
        initial_state: AgentState = {
            "objective": objective,
            "project_id": str(task.project_id),
            "task_id": str(task.id),
            "execution_id": str(execution_id),
            "context": [],
            "plan": [],
            "current_step_index": 0,
            "step_results": [],
            "step_count": 0,
            "max_steps": int(os.getenv("AGENT_MAX_STEPS", "10")),
            "retry_count": 0,
            "max_retries": int(os.getenv("AGENT_MAX_RETRIES", "2")),
            "final_answer": "",
            "status": "in_progress",
            "awaiting_approval": False,
        }

        try:
            workflow = WorkflowGraph(
                self.db,
                self.redis,
                self.executor,
                runtime=self.runtime,
                router=ModelRouter(),
                trace_sink=self.trace_sink,
                approval_gate=self.approval_gate,
            )
            final_state = await workflow.build().ainvoke(initial_state)
            if final_state.get("awaiting_approval"):
                return {
                    "status": "requires_approval",
                    "execution_id": str(execution_id),
                    "approval_id": final_state.get("approval_id"),
                    "steps_taken": final_state.get("current_step_index", 0),
                }
            if final_state.get("status") == "failed":
                return {
                    "status": "failed",
                    "execution_id": str(execution_id),
                    "error_detail": final_state.get("failure_reason", "Agent execution failed"),
                    "steps_taken": final_state.get("current_step_index", 0),
                    "tool_results": final_state.get("step_results", []),
                }
            return {
                "status": "success",
                "execution_id": str(execution_id),
                "final_answer": final_state.get("final_answer", ""),
                "steps_taken": final_state.get("current_step_index", 0),
                "tool_results": final_state.get("step_results", []),
            }
        except Exception as exc:
            logger.exception("Agent orchestration failed safely for task %s", task.id)
            return {
                "status": "error",
                "execution_id": str(execution_id),
                "error_detail": "Agent execution failed before completion",
            }
