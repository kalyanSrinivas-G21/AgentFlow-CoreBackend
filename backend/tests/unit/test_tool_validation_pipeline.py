# backend/tests/unit/test_tool_validation_pipeline.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from app.agents.executor import Executor
from app.tools.base import get_tool_catalog

pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_deps():
    db = AsyncMock()
    db.add = MagicMock()
    redis = AsyncMock()
    return db, redis

async def test_tool_catalog_generation():
    catalog = get_tool_catalog()
    assert len(catalog) > 0
    # Verify the catalog structure includes the schema
    assert "name" in catalog[0]
    assert "description" in catalog[0]
    assert "parameters" in catalog[0]

async def test_pipeline_rejects_unregistered_tool(mock_deps):
    db, redis = mock_deps
    executor = Executor(db, redis)
    
    plan_step = MagicMock()
    plan_step.id = uuid4()
    plan_step.step_number = 1
    plan_step.tool_name = "hallucinated.tool"
    plan_step.tool_args = {}
    
    # FIX: Mock task lookup to prevent dangling AsyncMock warnings
    task = MagicMock()
    task.project_id = uuid4()
    executor.repo.get_task = AsyncMock(return_value=task)
    
    result = await executor.execute_step(plan_step, uuid4())
    assert result.success is False
    assert "registry_error" in result.error

async def test_pipeline_rejects_invalid_schema(mock_deps):
    db, redis = mock_deps
    executor = Executor(db, redis)
    
    plan_step = MagicMock()
    plan_step.id = uuid4()
    plan_step.step_number = 1
    plan_step.tool_name = "filesystem.write" # Real tool
    plan_step.tool_args = {"path": "test.txt"} # Missing required 'content' field!
    
    # Task lookup needs to succeed to reach the validation stages
    task = MagicMock()
    task.project_id = uuid4()
    executor.repo.get_task = AsyncMock(return_value=task)
    
    result = await executor.execute_step(plan_step, uuid4())
    assert result.success is False
    
    # The schema error is caught defensively by either the Policy Engine or Stage 3.
    # We verify that it was cleanly rejected for invalid schema arguments.
    assert "schema_validation_error" in result.error or "Invalid arguments" in result.error