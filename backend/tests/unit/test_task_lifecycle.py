# backend/tests/unit/test_task_lifecycle.py
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, patch
from app.tasks.service import TaskService
from app.tasks.schemas import TaskCreateRequest
from app.tasks.models import Task, Project
from app.common.exceptions import InvalidTaskStateTransition

@pytest.fixture
def mock_db():
    return AsyncMock()

@pytest.fixture
def mock_redis():
    return AsyncMock()

@pytest.mark.asyncio
async def test_create_task_transitions_to_queued(mock_db, mock_redis):
    svc = TaskService(mock_db, mock_redis)
    project_id = uuid4()
    req = TaskCreateRequest(task_type="chat_probe", input_payload={"data": "test"})
    
    mock_project = Project(id=project_id, name="Test Project")
    svc.repo.get_project = AsyncMock(return_value=mock_project)
    
    def create_side_effect(task):
        task.id = uuid4()
        return task
    svc.repo.create_task = AsyncMock(side_effect=create_side_effect)
    
    def update_side_effect(task, status):
        task.status = status
        return task
    svc.repo.update_task_status = AsyncMock(side_effect=update_side_effect)

    with patch('app.tasks.service.publish', new_callable=AsyncMock) as mock_publish:
        task = await svc.create_task(project_id, req)
        
        assert task.status == "QUEUED"
        assert task.task_type == "chat_probe"
        
        # Verify 2 events were published (CREATED and QUEUED)
        assert mock_publish.call_count == 2
        calls = mock_publish.call_args_list
        assert calls[0][0][2].event_type == "task.created"
        assert calls[1][0][2].event_type == "task.queued"

@pytest.mark.asyncio
async def test_cancel_invalid_state_transition(mock_db, mock_redis):
    svc = TaskService(mock_db, mock_redis)
    task_id = uuid4()
    
    # Task is already completed
    mock_task = Task(id=task_id, status="COMPLETED")
    svc.repo.get_task = AsyncMock(return_value=mock_task)
    
    with pytest.raises(InvalidTaskStateTransition) as exc_info:
        await svc.cancel_task(task_id)
        
    assert exc_info.value.current_state == "COMPLETED"
    assert exc_info.value.target_state == "CANCEL_REQUESTED"

@pytest.mark.asyncio
async def test_retry_spawns_immutable_new_task(mock_db, mock_redis):
    svc = TaskService(mock_db, mock_redis)
    old_task_id = uuid4()
    
    # Existing failed task
    mock_task = Task(
        id=old_task_id, 
        project_id=uuid4(), 
        task_type="chat_probe", 
        status="FAILED", 
        input_payload={"test": 123}
    )
    svc.repo.get_task = AsyncMock(return_value=mock_task)
    
    def create_side_effect(task):
        task.id = uuid4() 
        return task
    svc.repo.create_task = AsyncMock(side_effect=create_side_effect)
    
    def update_side_effect(task, status):
        task.status = status
        return task
    svc.repo.update_task_status = AsyncMock(side_effect=update_side_effect)

    with patch('app.tasks.service.publish', new_callable=AsyncMock) as mock_publish:
        new_task = await svc.retry_task(old_task_id)
        
        # Ensure it's a new task ID and retains ancestry
        assert new_task.id != old_task_id
        assert new_task.retry_of_task_id == old_task_id
        assert new_task.status == "QUEUED"