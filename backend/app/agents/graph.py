import json
import logging
import os
import time
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Dict, List, TypedDict
from uuid import UUID, uuid4

from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from app.agents.approval import ApprovalGate
from app.agents.contracts import ExecutionTraceEvent, ExecutionTraceSink
from app.models_ai.contracts import ModelInferenceRequest, ModelRuntime
from app.models_ai.router_v2 import ModelRouter
from app.models_ai.runtime import OllamaRuntime
from app.tools.base import get_tool_catalog

logger = logging.getLogger(__name__)


class ToolCall(BaseModel):
    tool: str = Field(description="Name of a registered tool")
    tool_args: Dict[str, Any] = Field(default_factory=dict)


class AgentPlan(BaseModel):
    steps: List[ToolCall] = Field(default_factory=list)


class AgentState(TypedDict, total=False):
    objective: str
    project_id: str
    task_id: str
    execution_id: str
    context: List[Dict[str, str]]
    plan: List[Dict[str, Any]]
    current_step_index: int
    step_results: List[Dict[str, Any]]
    step_count: int
    max_steps: int
    retry_count: int
    max_retries: int
    final_answer: str
    status: str
    awaiting_approval: bool
    approval_id: str
    failure_reason: str


class WorkflowGraph:
    """Bounded agent graph with safe trace events and no model reasoning exposure."""

    def __init__(
        self,
        db,
        redis,
        executor,
        *,
        runtime: ModelRuntime | None = None,
        router: ModelRouter | None = None,
        trace_sink: ExecutionTraceSink | None = None,
        approval_gate: ApprovalGate | None = None,
        approval_required_tools: set[str] | None = None,
    ):
        self.db = db
        self.redis = redis
        self.executor = executor
        self.runtime = runtime or OllamaRuntime()
        self.router = router or ModelRouter()
        self.model_id = self.router.route(required_capabilities=["tool_calling"])
        self.trace_sink = trace_sink
        self.approval_gate = approval_gate
        self.approval_required_tools = approval_required_tools or {
            item.strip() for item in os.getenv("APPROVAL_REQUIRED_TOOLS", "").split(",") if item.strip()
        }

    async def _trace(
        self,
        state: AgentState,
        step_type: str,
        status: str,
        component: str,
        summary: str,
        *,
        step_id: UUID | None = None,
        started_at: datetime | None = None,
        retry_number: int = 0,
        error_category: str | None = None,
    ) -> None:
        if self.trace_sink is None:
            return
        start = started_at or datetime.now(timezone.utc)
        end = datetime.now(timezone.utc)
        duration_ms = max(0, int((end - start).total_seconds() * 1000))
        event = ExecutionTraceEvent(
            task_id=UUID(state["task_id"]),
            execution_id=UUID(state["execution_id"]),
            step_id=step_id or uuid4(),
            step_type=step_type,
            component=component,
            start_time=start,
            end_time=end,
            duration_ms=duration_ms,
            status=status,
            retry_number=retry_number,
            error_category=error_category,
            safe_summary=summary,
        )
        await self.trace_sink.append(event)

    async def plan_node(self, state: AgentState) -> AgentState:
        started = datetime.now(timezone.utc)
        await self._trace(state, "planning", "in_progress", "orchestrator", "Building execution plan", started_at=started)
        catalog = json.dumps(get_tool_catalog(), indent=2)
        history = "\n".join(f"{msg['role']}: {msg['content']}" for msg in state.get("context", []))
        prompt = f"Objective: {state['objective']}\n\nHistory:\n{history}\n\nAvailable tools:\n{catalog}\n\nReturn only JSON with a steps array."
        try:
            response = await self.runtime.run_inference(
                ModelInferenceRequest(
                    model_id=self.model_id,
                    prompt=prompt,
                    system="Select only registered tools. Do not include private reasoning.",
                    task_id=UUID(state["task_id"]),
                    execution_id=UUID(state["execution_id"]),
                )
            )
            start = response.find("{")
            end = response.rfind("}") + 1
            clean_json = response[start:end] if start >= 0 and end > start else response
            plan_data = AgentPlan.model_validate_json(clean_json)
            state["plan"] = [step.model_dump() for step in plan_data.steps]
            state["current_step_index"] = 0
            state["step_count"] = state.get("step_count", 0) + 1
            await self._trace(state, "planning", "succeeded", "orchestrator", f"Plan created with {len(plan_data.steps)} registered steps", started_at=started)
        except Exception as exc:
            state["status"] = "failed"
            state["failure_reason"] = "Model returned an invalid execution plan"
            state["final_answer"] = "Execution could not start because the local model returned an invalid plan."
            await self._trace(state, "planning", "failed", "orchestrator", "Local model plan validation failed", started_at=started, error_category="validation")
            logger.warning("Plan validation failed for task %s: %s", state["task_id"], exc)
        return state

    async def execute_node(self, state: AgentState) -> AgentState:
        if state.get("status") == "failed" or state.get("awaiting_approval"):
            return state
        if state["current_step_index"] >= len(state.get("plan", [])):
            return state

        step_data = state["plan"][state["current_step_index"]]
        step_id = uuid4()
        tool_name = step_data["tool"]
        if tool_name in self.approval_required_tools and self.approval_gate is not None:
            request = await self.approval_gate.request(
                UUID(state["task_id"]), UUID(state["execution_id"]), tool_name, "high"
            )
            state["awaiting_approval"] = True
            state["approval_id"] = str(request.approval_id)
            await self._trace(state, "approval", "in_progress", "approval_gate", f"Approval required for {tool_name}", step_id=step_id)
            return state

        started = datetime.now(timezone.utc)
        await self._trace(state, "tool_execution", "in_progress", "tool_executor", f"Executing registered tool {tool_name}", step_id=step_id, started_at=started)

        plan_step = SimpleNamespace(
            id=step_id,
            step_number=state["current_step_index"] + 1,
            tool_name=tool_name,
            tool_args=step_data.get("tool_args", {}),
            status="PENDING",
        )

        try:
            result = await self.executor.execute_step(plan_step, state["task_id"])
            success = bool(result.success)
            state["step_results"].append({
                "step": plan_step.step_number,
                "tool": tool_name,
                "success": success,
                "output": result.output,
                "error": result.error,
            })
            state["current_step_index"] += 1
            await self._trace(
                state,
                "tool_execution",
                "succeeded" if success else "failed",
                "tool_executor",
                f"Tool {tool_name} {'completed' if success else 'failed'}",
                step_id=step_id,
                started_at=started,
                error_category=None if success else "tool",
            )
        except Exception as exc:
            state["step_results"].append({"step": plan_step.step_number, "tool": tool_name, "success": False, "output": None, "error": "tool execution failed"})
            state["current_step_index"] += 1
            await self._trace(state, "tool_execution", "failed", "tool_executor", f"Tool {tool_name} failed safely", step_id=step_id, started_at=started, error_category="tool")
            logger.warning("Tool execution failed for task %s: %s", state["task_id"], exc)
        return state

    async def observe_node(self, state: AgentState) -> AgentState:
        if state.get("status") == "failed":
            return state
        if state.get("step_results"):
            last_result = state["step_results"][-1]
            outcome = f"Tool {last_result['tool']} completed with status {'success' if last_result['success'] else 'failure'}"
            state.setdefault("context", []).append({"role": "system", "content": outcome})
        return state

    async def reason_node(self, state: AgentState) -> AgentState:
        if state.get("status") == "failed":
            return state
        last_result = state.get("step_results", [])[-1:] or [None]
        if last_result[0] is not None and not last_result[0]["success"]:
            await self._trace(state, "validation", "failed", "validator", "Tool result failed validation", error_category="tool")
            state["retry_count"] = state.get("retry_count", 0) + 1
            if state["retry_count"] > state.get("max_retries", 2):
                state["status"] = "failed"
                state["failure_reason"] = "Bounded validation retries exhausted"
                state["final_answer"] = "Execution failed after bounded validation retries."
                return state
            state["plan"] = []
            return state

        if state.get("step_count", 0) >= state.get("max_steps", 10):
            state["status"] = "failed"
            state["failure_reason"] = "Maximum execution steps reached"
            state["final_answer"] = "Execution stopped at the configured step limit."
            await self._trace(state, "validation", "failed", "validator", "Maximum execution steps reached", error_category="resource")
            return state

        try:
            response = await self.runtime.run_inference(
                ModelInferenceRequest(
                    model_id=self.model_id,
                    prompt=f"Objective: {state['objective']}\nAssess whether the registered tool results complete it. Reply COMPLETE or CONTINUE.",
                    system="Return only COMPLETE or CONTINUE. Do not include private reasoning.",
                    task_id=UUID(state["task_id"]),
                    execution_id=UUID(state["execution_id"]),
                )
            )
            if response.strip().upper().startswith("COMPLETE"):
                state["final_answer"] = "Task completed by the registered execution steps."
                state["status"] = "succeeded"
                await self._trace(state, "validation", "succeeded", "validator", "Execution result validated")
            else:
                state["final_answer"] = ""
        except Exception:
            state["status"] = "failed"
            state["failure_reason"] = "Local validation model unavailable"
            state["final_answer"] = "Execution could not be validated because the local model was unavailable."
            await self._trace(state, "validation", "failed", "validator", "Local validation model unavailable", error_category="model")
        return state

    def should_continue(self, state: AgentState) -> str:
        if state.get("awaiting_approval") or state.get("status") in {"failed", "succeeded"}:
            return END
        if state.get("final_answer"):
            return END
        if state.get("current_step_index", 0) < len(state.get("plan", [])):
            return "execute"
        return "plan"

    def build(self) -> StateGraph:
        workflow = StateGraph(AgentState)
        workflow.add_node("plan", self.plan_node)
        workflow.add_node("execute", self.execute_node)
        workflow.add_node("observe", self.observe_node)
        workflow.add_node("reason", self.reason_node)
        workflow.set_entry_point("plan")
        workflow.add_edge("plan", "execute")
        workflow.add_edge("execute", "observe")
        workflow.add_edge("observe", "reason")
        workflow.add_conditional_edges("reason", self.should_continue)
        return workflow.compile()
