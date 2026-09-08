# backend/tests/e2e/test_slice3_agent_writes_file.py
"""
Slice 3 E2E: Agent writes a file.

Intent: Prove that the full orchestration chain
    AgentOrchestrator → WorkflowGraph (plan → execute → observe → reason)
drives the executor to write a file and returns a successful result dict.

Architecture under test (current):
    AgentOrchestrator.run(task)
        └── WorkflowGraph.build().ainvoke(state)
                ├── plan_node   ← mocked OllamaProvider.generate
                ├── execute_node ← mocked executor.execute_step
                ├── observe_node
                └── reason_node ← mocked OllamaProvider.generate

Mocked boundaries:
    - OllamaProvider.generate  (non-deterministic LLM; patched at module level)
    - executor.execute_step    (sandbox/filesystem; injected via orchestrator ctor)
    - trace_sink               (InMemoryExecutionTraceSink — avoids unawaited
                                AsyncMock coroutine warnings from SqlAlchemy db.add)

Preserved requirement:
    The agent completes a plan→execute→reason cycle and returns status="success"
    with step_results that confirm the filesystem.write tool was invoked.
"""
import json
import pytest
import uuid
from unittest.mock import AsyncMock, patch
from app.agents.orchestrator import AgentOrchestrator
from app.agents.trace_store import InMemoryExecutionTraceSink
from app.tools.models import ToolResult
from app.tasks.models import Task

pytestmark = pytest.mark.asyncio


@patch("app.models_ai.ollama_provider.OllamaProvider.generate")
async def test_agent_writes_file_e2e(mock_generate):
    """
    Proves that AgentOrchestrator drives the LangGraph WorkflowGraph through a
    complete plan → execute → reason cycle and returns a successful result.

    Replaces legacy test that called orchestrator.executor.repo.get_task (an
    internal implementation detail that no longer matches the current architecture).
    """
    # ----------------------------------------------------------------
    # LLM responses in order:
    #   1. plan_node: return a plan with one filesystem.write step
    #   2. reason_node: declare the plan complete
    # ----------------------------------------------------------------
    mock_generate.side_effect = [
        json.dumps({
            "steps": [{
                "tool": "filesystem.write",
                "tool_args": {"path": "agent_test.txt", "content": "I am alive"},
            }]
        }),
        "COMPLETE",
    ]

    # ----------------------------------------------------------------
    # Executor mock: simulate successful tool execution
    # ----------------------------------------------------------------
    executor_mock = AsyncMock()
    executor_mock.execute_step = AsyncMock(
        return_value=ToolResult(
            success=True,
            output="File written: agent_test.txt",
        )
    )

    # ----------------------------------------------------------------
    # Task mock: minimal Task object that satisfies orchestrator.run()
    # ----------------------------------------------------------------
    task = Task(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        status="RUNNING",
        task_type="agentic_workflow",
        input_payload={"prompt": "Write a test file"},
    )

    db_mock = AsyncMock()
    redis_mock = AsyncMock()

    orchestrator = AgentOrchestrator(
        db_mock,
        redis_mock,
        executor=executor_mock,
        trace_sink=InMemoryExecutionTraceSink(),  # avoids unawaited AsyncMock coroutine warnings
    )

    # ----------------------------------------------------------------
    # Execute the full LangGraph orchestration path
    # ----------------------------------------------------------------
    result = await orchestrator.run(task)

    # ----------------------------------------------------------------
    # Assertions
    # ----------------------------------------------------------------
    assert result["status"] == "success", (
        f"Expected status=success, got: {result}"
    )
    assert result["steps_taken"] == 1, (
        f"Expected 1 step executed, got steps_taken={result['steps_taken']}"
    )

    # The executor must have been driven once by the WorkflowGraph
    executor_mock.execute_step.assert_called_once()
    call_args = executor_mock.execute_step.call_args[0]
    plan_step = call_args[0]
    assert plan_step.tool_name == "filesystem.write", (
        f"Expected tool filesystem.write, got: {plan_step.tool_name}"
    )

    # Step results surfaced through the orchestrator result dict
    tool_results = result.get("tool_results", [])
    assert len(tool_results) == 1
    assert tool_results[0]["tool"] == "filesystem.write"
    assert tool_results[0]["success"] is True
