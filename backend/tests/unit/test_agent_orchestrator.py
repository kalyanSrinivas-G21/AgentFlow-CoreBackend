# backend/tests/unit/test_agent_orchestrator.py
import pytest
import uuid
import os
from unittest.mock import AsyncMock, MagicMock, patch
from app.agents.orchestrator import AgentOrchestrator
from app.tools.models import ToolResult

async def mock_db_refresh(obj):
    """Simulate SQLAlchemy populating the ID after a commit/refresh."""
    if not getattr(obj, 'id', None):
        obj.id = uuid.uuid4()

def create_db_mock():
    db_mock = AsyncMock()
    db_mock.add = MagicMock()
    db_mock.refresh = AsyncMock(side_effect=mock_db_refresh)
    return db_mock

@pytest.mark.asyncio
async def test_agent_orchestrator_success():
    db_mock = create_db_mock()
    redis_mock = AsyncMock()
    
    task_mock = MagicMock()
    task_mock.id = uuid.uuid4()
    task_mock.project_id = uuid.uuid4()
    task_mock.status = "RUNNING"
    task_mock.input_payload = {"prompt": "Do something"}

    executor_mock = AsyncMock()
    executor_mock.execute_step = AsyncMock(return_value=ToolResult(success=True, output="Mock output"))

    orchestrator = AgentOrchestrator(db_mock, redis_mock, executor=executor_mock)
    
    # Mock the LLM responses to simulate a successful single-step execution
    with patch("app.models_ai.ollama_provider.OllamaProvider.generate") as mock_generate:
        mock_generate.side_effect = [
            '{"steps": [{"tool": "mock_tool", "tool_args": {"key": "val"}}], "reasoning": "Test step"}', # Plan
            'COMPLETE' # Reason
        ]
        
        result = await orchestrator.run(task_mock)
    
    assert result["status"] == "success"
    assert executor_mock.execute_step.call_count == 1

@pytest.mark.asyncio
async def test_agent_orchestrator_retry_then_pass():
    db_mock = create_db_mock()
    redis_mock = AsyncMock()
    
    task_mock = MagicMock()
    task_mock.id = uuid.uuid4()
    task_mock.project_id = uuid.uuid4()
    task_mock.status = "RUNNING"
    task_mock.input_payload = {"prompt": "Do something"}

    executor_mock = AsyncMock()
    executor_mock.execute_step = AsyncMock(return_value=ToolResult(success=True, output="Mock output"))

    orchestrator = AgentOrchestrator(db_mock, redis_mock, executor=executor_mock)
    
    # Mock the LLM responses to simulate a retry scenario
    with patch("app.models_ai.ollama_provider.OllamaProvider.generate") as mock_generate:
        mock_generate.side_effect = [
            '{"steps": [{"tool": "mock_tool", "tool_args": {}}], "reasoning": "Test step"}', # Plan 1
            'CONTINUE: Need more info', # Reason 1 - triggers retry
            '{"steps": [{"tool": "mock_tool", "tool_args": {}}], "reasoning": "Test step again"}', # Plan 2
            'COMPLETE' # Reason 2
        ]
        
        result = await orchestrator.run(task_mock)
    
    assert result["status"] == "success"
    # Should have executed 2 steps (1 retry)
    assert executor_mock.execute_step.call_count == 2

@pytest.mark.asyncio
async def test_agent_orchestrator_hard_cap():
    db_mock = create_db_mock()
    redis_mock = AsyncMock()
    
    task_mock = MagicMock()
    task_mock.id = uuid.uuid4()
    task_mock.project_id = uuid.uuid4()
    task_mock.status = "RUNNING"
    task_mock.input_payload = {"prompt": "Do something"}

    executor_mock = AsyncMock()
    executor_mock.execute_step = AsyncMock(return_value=ToolResult(success=True, output="Mock output"))

    # Set a low max steps for testing
    os.environ["AGENT_MAX_STEPS"] = "3"
    
    orchestrator = AgentOrchestrator(db_mock, redis_mock, executor=executor_mock)
    
    # Mock the LLM responses to simulate many steps
    with patch("app.models_ai.ollama_provider.OllamaProvider.generate") as mock_generate:
        # Plan 1, Continue, Plan 2, Continue, Plan 3, Continue, Plan 4, Continue (should hit cap)
        mock_generate.side_effect = [
            '{"steps": [{"tool": "tool_1", "tool_args": {}}], "reasoning": "Step 1"}',
            'CONTINUE',
            '{"steps": [{"tool": "tool_2", "tool_args": {}}], "reasoning": "Step 2"}',
            'CONTINUE',
            '{"steps": [{"tool": "tool_3", "tool_args": {}}], "reasoning": "Step 3"}',
            'CONTINUE',
            '{"steps": [{"tool": "tool_4", "tool_args": {}}], "reasoning": "Step 4"}',
            'CONTINUE',
        ]
        
        result = await orchestrator.run(task_mock)
    
    # Should fail due to step limit
    assert result["status"] == "failed"
    assert "step" in result.get("error_detail", "").lower() or "limit" in result.get("error_detail", "").lower()
    
    # Clean up
    del os.environ["AGENT_MAX_STEPS"]