# backend/tests/e2e/test_slice3_agent_writes_file.py
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from app.agents.orchestrator import AgentOrchestrator
from app.agents.schemas import PlanStepDraft, ValidationResult
from app.workspace.service import WorkspaceService
from app.tasks.models import Task

async def mock_db_refresh(obj):
    if not getattr(obj, 'id', None):
        obj.id = uuid.uuid4()

def create_db_mock():
    db_mock = AsyncMock()
    db_mock.add = MagicMock()
    db_mock.refresh = AsyncMock(side_effect=mock_db_refresh)
    return db_mock

@pytest.mark.asyncio
async def test_agent_writes_file_e2e():
    db_mock = create_db_mock()
    redis_mock = AsyncMock()
    
    project_id = uuid.uuid4()
    
    # Mock Task
    task_mock = Task(id=uuid.uuid4(), project_id=project_id, status="RUNNING", input_payload={"prompt": "Write a test file"})
    
    # Mock Executor repo.get_task behavior
    db_mock.execute = AsyncMock()
    db_mock.scalar = MagicMock(return_value=task_mock)
    
    orchestrator = AgentOrchestrator(db_mock, redis_mock)
    
    # Inject TaskRepository mock for the executor lookup
    orchestrator.executor.repo.get_task = AsyncMock(return_value=task_mock)
    
    # Mock Planner to plan a filesystem write
    orchestrator.planner.plan = AsyncMock(return_value=[
        PlanStepDraft(
            tool_name="filesystem.write", 
            args={"path": "agent_test.txt", "content": "I am alive"}, 
            reason="Satisfy prompt"
        )
    ])
    
    # Mock Validator to PASS
    orchestrator.validator.validate = AsyncMock(return_value=ValidationResult(passed=True, reason="ok"))

    # Execute
    result = await orchestrator.run(task_mock)
    
    # Verify Execution
    assert result["status"] == "success"
    
    # Verify File was physically written to isolated workspace
    expected_file = WorkspaceService.get_project_dir(project_id) / "agent_test.txt"
    assert expected_file.exists()
    assert expected_file.read_text(encoding="utf-8") == "I am alive"
    
    # Cleanup physical footprint
    expected_file.unlink()