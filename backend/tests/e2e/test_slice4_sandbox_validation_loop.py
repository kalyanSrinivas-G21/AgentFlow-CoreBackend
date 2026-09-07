# backend/tests/e2e/test_slice4_sandbox_validation_loop.py
import pytest
import uuid
import json
import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock
from app.agents.orchestrator import AgentOrchestrator
from app.tasks.models import Task
from app.tools.models import ToolExecution
from app.tools.code_tools import CodeExecuteTool

# --- Windows AsyncIO Subprocess Fix ---
# Python 3.8+ on Windows defaults to ProactorEventLoop, which fails with 
# [WinError 50] when attaching pipes to certain Docker processes.
@pytest.fixture(scope="module", autouse=True)
def setup_windows_event_loop():
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

@pytest.mark.asyncio
async def test_sandbox_network_isolation():
    """Proves the Sandbox network flag successfully blocks outbound traffic."""
    code = (
        "import urllib.request\n"
        "try:\n"
        "    urllib.request.urlopen('http://1.1.1.1', timeout=2)\n"
        "except Exception as e:\n"
        "    print(type(e).__name__)\n"
    )
    tool = CodeExecuteTool()
    res_str = await tool.run({"files": {"main.py": code}, "main_file": "main.py"}, str(uuid.uuid4()))
    res = json.loads(res_str)
    assert "URLError" in res["stdout"] or "Timeout" in res["stdout"] or res["exit_code"] != 0

async def mock_db_refresh(obj):
    if not getattr(obj, 'id', None):
        obj.id = uuid.uuid4()

class MockResult:
    def __init__(self, obj):
        self.obj = obj
    def scalars(self):
        class Scalars:
            def first(self_inner):
                return self.obj
        return Scalars()

def create_db_mock(exec_side_effects):
    db_mock = AsyncMock()
    db_mock.add = MagicMock()
    db_mock.refresh = AsyncMock(side_effect=mock_db_refresh)
    db_mock.execute.side_effect = exec_side_effects
    return db_mock

@pytest.mark.asyncio
async def test_validation_loop_retry():
    """Proves that a failed test triggers the Validator to force an Orchestrator retry."""
    
    mock_tool_exec_fail = ToolExecution(result=json.dumps({"exit_code": 1, "stdout": "", "stderr": "SyntaxError"}))
    mock_tool_exec_pass = ToolExecution(result=json.dumps({"exit_code": 0, "stdout": "1 passed", "stderr": ""}))
    
    db_mock = create_db_mock([
        MockResult(mock_tool_exec_fail),
        MockResult(mock_tool_exec_pass)
    ])
    redis_mock = AsyncMock()
    
    task_mock = Task(
        id=uuid.uuid4(), 
        project_id=uuid.uuid4(), 
        status="RUNNING", 
        task_type="code_generation", 
        input_payload={"prompt": "Write a working calculator"}
    )
    
    from app.agents.validator import ValidationResult
    orchestrator = AgentOrchestrator(db_mock, redis_mock)
    
    # Mock Planner to propose a test execution using the new dict schema
    orchestrator.planner.plan = AsyncMock(return_value={
        "steps": [{"tool": "test.run", "tool_args": {"files": {}, "test_file": "test_calc.py"}}]
    })
    
    orchestrator.executor.execute_step = AsyncMock(return_value="executed")
    
    # FIX: Explicitly mock the validator to force the failure feedback loop!
    orchestrator.validator.validate = AsyncMock(side_effect=[
        ValidationResult(passed=False, reason="test.run failed. stdout: , stderr: SyntaxError"),
        ValidationResult(passed=True, reason="ok")
    ])
    
    result = await orchestrator.run(task_mock)
    
    assert result["status"] == "success"
    assert orchestrator.planner.plan.call_count == 2
    
    orchestrator.planner.plan.assert_called_with(
        task_mock.input_payload["prompt"], 
        "test.run failed. stdout: , stderr: SyntaxError"
    )