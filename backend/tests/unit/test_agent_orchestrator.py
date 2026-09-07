# backend/tests/unit/test_agent_orchestrator.py
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from app.agents.orchestrator import AgentOrchestrator
from app.agents.validator import ValidationResult

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
    task_mock.status = "RUNNING"
    task_mock.input_payload = {"prompt": "Do something"}

    orchestrator = AgentOrchestrator(db_mock, redis_mock)
    
    # Mock Planner to return 1 step
    orchestrator.planner.plan = AsyncMock(return_value={
        "steps": [{"tool": "mock_tool", "tool_args": {"key": "val"}}]
    })
    
    # Mock Executor
    orchestrator.executor.execute_step = AsyncMock()
    
    # Mock Validator to PASS
    orchestrator.validator.validate = AsyncMock(return_value=ValidationResult(passed=True, reason="ok"))

    result = await orchestrator.run(task_mock)
    
    assert result["status"] == "success"
    assert orchestrator.planner.plan.call_count == 1
    assert orchestrator.executor.execute_step.call_count == 1
    assert orchestrator.validator.validate.call_count == 1

@pytest.mark.asyncio
async def test_agent_orchestrator_retry_then_pass():
    db_mock = create_db_mock()
    redis_mock = AsyncMock()
    
    task_mock = MagicMock()
    task_mock.id = uuid.uuid4()
    task_mock.status = "RUNNING"
    task_mock.input_payload = {"prompt": "Do something"}

    orchestrator = AgentOrchestrator(db_mock, redis_mock)
    orchestrator.planner.plan = AsyncMock(return_value={
        "steps": [{"tool": "mock_tool", "tool_args": {}}]
    })
    orchestrator.executor.execute_step = AsyncMock()
    
    # Validator fails first time, passes second time
    orchestrator.validator.validate = AsyncMock(side_effect=[
        ValidationResult(passed=False, reason="Missing info"),
        ValidationResult(passed=True, reason="Looks good now")
    ])

    result = await orchestrator.run(task_mock)
    
    assert result["status"] == "success"
    # Should have planned twice (1 retry)
    assert orchestrator.planner.plan.call_count == 2
    # Second plan call should have received the prior failure
    orchestrator.planner.plan.assert_called_with("Do something", "Missing info")
    assert orchestrator.executor.execute_step.call_count == 2
    assert orchestrator.validator.validate.call_count == 2

@pytest.mark.asyncio
async def test_agent_orchestrator_hard_cap():
    db_mock = create_db_mock()
    redis_mock = AsyncMock()
    
    task_mock = MagicMock()
    task_mock.id = uuid.uuid4()
    task_mock.status = "RUNNING"
    task_mock.input_payload = {"prompt": "Do something"}

    orchestrator = AgentOrchestrator(db_mock, redis_mock)
    
    # Planner returns 10 steps (above the cap of 6)
    orchestrator.planner.plan = AsyncMock(return_value={
        "steps": [{"tool": f"tool_{i}", "tool_args": {}} for i in range(10)]
    })
    orchestrator.executor.execute_step = AsyncMock()
    orchestrator.validator.validate = AsyncMock(return_value=ValidationResult(passed=True, reason="ok"))

    result = await orchestrator.run(task_mock)
    
    assert result["status"] == "success"
    # Executor should have only been called 6 times due to the hard cap
    assert orchestrator.executor.execute_step.call_count == 6