from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.agents.approval import InMemoryApprovalGate
from app.agents.graph import AgentState, WorkflowGraph
from app.agents.trace_store import InMemoryExecutionTraceSink
from app.models_ai.contracts import ModelInferenceRequest


class FakeRuntime:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []

    async def run_inference(self, request: ModelInferenceRequest):
        self.requests.append(request)
        return next(self.responses)


class FakeExecutor:
    def __init__(self, success=True):
        self.success = success
        self.calls = 0

    async def execute_step(self, step, task_id):
        self.calls += 1
        return SimpleNamespace(
            success=self.success,
            output="tool output" if self.success else None,
            error=None if self.success else "controlled tool failure",
        )


def initial_state():
    task_id = uuid4()
    return AgentState(
        objective="perform the registered task",
        project_id=str(uuid4()),
        task_id=str(task_id),
        execution_id=str(uuid4()),
        context=[],
        plan=[],
        current_step_index=0,
        step_results=[],
        step_count=0,
        max_steps=4,
        retry_count=0,
        max_retries=1,
        final_answer="",
        status="in_progress",
        awaiting_approval=False,
    )


@pytest.mark.asyncio
async def test_successful_graph_emits_safe_trace_without_reasoning():
    runtime = FakeRuntime(['{"steps":[{"tool":"safe_tool","tool_args":{}}]}', "COMPLETE"])
    sink = InMemoryExecutionTraceSink()
    graph = WorkflowGraph(None, None, FakeExecutor(), runtime=runtime, trace_sink=sink)

    result = await graph.build().ainvoke(initial_state())

    assert result["status"] == "succeeded"
    assert any(event.step_type == "planning" for event in sink.events)
    assert any(event.step_type == "tool_execution" for event in sink.events)
    assert any(event.step_type == "validation" and event.status == "succeeded" for event in sink.events)
    assert all("reasoning" not in event.__class__.model_fields for event in sink.events)
    assert all("private" not in (event.safe_summary or "").lower() for event in sink.events)


@pytest.mark.asyncio
async def test_invalid_plan_surfaces_failed_trace_instead_of_empty_success():
    runtime = FakeRuntime(["not valid json"])
    sink = InMemoryExecutionTraceSink()
    graph = WorkflowGraph(None, None, FakeExecutor(), runtime=runtime, trace_sink=sink)

    result = await graph.build().ainvoke(initial_state())

    assert result["status"] == "failed"
    assert "invalid" in result["failure_reason"].lower()
    assert any(event.step_type == "planning" and event.status == "failed" for event in sink.events)


@pytest.mark.asyncio
async def test_tool_validation_failure_is_failed_and_bounded():
    runtime = FakeRuntime([
        '{"steps":[{"tool":"safe_tool","tool_args":{}}]}',
        '{"steps":[{"tool":"safe_tool","tool_args":{}}]}',
    ])
    sink = InMemoryExecutionTraceSink()
    graph = WorkflowGraph(None, None, FakeExecutor(success=False), runtime=runtime, trace_sink=sink)

    result = await graph.build().ainvoke(initial_state())

    assert result["status"] == "failed"
    assert "retries" in result["failure_reason"]
    assert any(event.step_type == "validation" and event.status == "failed" for event in sink.events)
    assert len(sink.events) < 20


@pytest.mark.asyncio
async def test_high_impact_tool_pauses_for_approval():
    runtime = FakeRuntime(['{"steps":[{"tool":"delete_file","tool_args":{}}]}'])
    sink = InMemoryExecutionTraceSink()
    gate = InMemoryApprovalGate()
    graph = WorkflowGraph(
        None,
        None,
        FakeExecutor(),
        runtime=runtime,
        trace_sink=sink,
        approval_gate=gate,
        approval_required_tools={"delete_file"},
    )

    result = await graph.build().ainvoke(initial_state())

    assert result["awaiting_approval"] is True
    assert result["approval_id"]
    assert len(gate.requests) == 1
    assert any(event.step_type == "approval" and event.status == "in_progress" for event in sink.events)
