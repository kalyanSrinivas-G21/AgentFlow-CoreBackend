# backend/tests/e2e/test_langgraph_agent.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from app.agents.graph import WorkflowGraph
from app.tools.models import ToolResult

pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_deps():
    db = AsyncMock()
    redis = AsyncMock()
    executor = AsyncMock()
    # Mock executor to return a standardized success payload from Phase 5
    executor.execute_step.return_value = ToolResult(success=True, output="Mock Tool Output")
    return db, redis, executor

@patch("app.models_ai.ollama_provider.OllamaProvider.generate")
async def test_langgraph_e2e_sequence(mock_generate, mock_deps):
    db, redis, executor = mock_deps
    
    # Mock the LLM responses to simulate a dynamic sequence
    # 1. Plan node generates a step
    # 2. Reason node determines it is NOT complete, causing replan
    # 3. Plan node generates final step
    # 4. Reason node determines it IS complete
    mock_generate.side_effect = [
        '{"steps": [{"tool": "filesystem.write", "tool_args": {"path": "test.txt", "content": "hello"}}], "reasoning": "Writing file"}', # Plan 1
        'CONTINUE: Need to verify file', # Reason 1
        '{"steps": [{"tool": "filesystem.read", "tool_args": {"path": "test.txt"}}], "reasoning": "Reading file"}', # Plan 2
        'COMPLETE: File was written and verified.' # Reason 2
    ]
    
    graph_builder = WorkflowGraph(db, redis, executor)
    app = graph_builder.build()
    
    initial_state = {
        "objective": "Write and read a file",
        "project_id": str(uuid4()),
        "task_id": str(uuid4()),
        "context": [{"role": "user", "content": "Write and read a file"}],
        "plan": [],
        "current_step_index": 0,
        "step_results": [],
        "step_count": 0,
        "max_steps": 5,
        "final_answer": ""
    }
    
    final_state = await app.ainvoke(initial_state)
    
    # Assertions validating the mandatory graph requirements
    
    # 1. Termination Condition Honored
    assert final_state["final_answer"] == "File was written and verified."
    assert final_state["step_count"] == 2 # Two planning cycles
    
    # 2. Execution routed through our Phase 5 Executor
    assert executor.execute_step.call_count == 2
    
    # 3. The graph dynamically observed results
    assert len(final_state["step_results"]) == 2
    assert final_state["step_results"][0]["output"] == "Mock Tool Output"
    assert "Mock Tool Output" in final_state["context"][1]["content"] # Output was added to context