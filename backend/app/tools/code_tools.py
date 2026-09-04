# backend/app/tools/code_tools.py
from typing import Dict, Any
from pydantic import BaseModel, Field
from app.tools.base import Tool, register_tool
from app.sandbox.runner import run_in_sandbox
import json

class CodeExecuteInput(BaseModel):
    files: Dict[str, str] = Field(..., description="Map of filename to code content.")
    main_file: str = Field(..., description="The python file to execute.")

@register_tool
class CodeExecuteTool(Tool):
    name = "code.execute"
    input_schema = CodeExecuteInput
    timeout_s = 30.0
    retryable = False

    async def run(self, args: Dict[str, Any], project_id: str) -> str:
        parsed = self.input_schema(**args)
        result = await run_in_sandbox(parsed.files, ["python", parsed.main_file], timeout_s=self.timeout_s)
        return json.dumps({
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.exit_code
        })

class TestRunInput(BaseModel):
    files: Dict[str, str] = Field(..., description="Map of filename to code content, including test files.")
    test_file: str = Field(..., description="The pytest file to run.")

@register_tool
class TestRunTool(Tool):
    name = "test.run"
    input_schema = TestRunInput
    timeout_s = 30.0
    retryable = False

    async def run(self, args: Dict[str, Any], project_id: str) -> str:
        parsed = self.input_schema(**args)
        result = await run_in_sandbox(parsed.files, ["pytest", "-q", parsed.test_file], timeout_s=self.timeout_s)
        return json.dumps({
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.exit_code
        })