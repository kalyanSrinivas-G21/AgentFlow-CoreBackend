# backend/app/tools/code_tools.py
from typing import Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.tools.base import Tool, register_tool
from app.tools.models import ToolResult
from app.sandbox.runner import run_in_sandbox

class CodeExecuteInput(BaseModel):
    files: Dict[str, str] = Field(..., description="Map of filename to code content.")
    main_file: str = Field(..., description="The python file to execute.")

@register_tool
class CodeExecuteTool(Tool):
    name = "code.execute"
    description = "Executes arbitrary python code inside an isolated Docker sandbox."
    input_schema = CodeExecuteInput
    timeout_s = 30.0
    retryable = False

    async def run(self, args: Dict[str, Any], project_id: str, db: AsyncSession = None) -> ToolResult:
        try:
            result = await run_in_sandbox(args["files"], ["python", args["main_file"]], timeout_s=self.timeout_s)
        except TimeoutError:
            return ToolResult(success=False, error="timeout", metadata={"exit_code": None})
        
        success = result.exit_code == 0
        output_payload = result.stdout if success else result.stderr
        
        return ToolResult(
            success=success,
            output=output_payload,
            error=result.stderr if not success else None,
            metadata={"exit_code": result.exit_code}
        )

class TestRunInput(BaseModel):
    files: Dict[str, str] = Field(..., description="Map of filename to code content, including test files.")
    test_file: str = Field(..., description="The pytest file to run.")

@register_tool
class TestRunTool(Tool):
    name = "test.run"
    description = "Executes pytest against provided files inside the sandbox."
    input_schema = TestRunInput
    timeout_s = 30.0
    retryable = False

    async def run(self, args: Dict[str, Any], project_id: str, db: AsyncSession = None) -> ToolResult:
        try:
            result = await run_in_sandbox(args["files"], ["pytest", "-q", args["test_file"]], timeout_s=self.timeout_s)
        except TimeoutError:
            return ToolResult(success=False, error="timeout", metadata={"exit_code": None})
        
        success = result.exit_code == 0
        output_payload = result.stdout if success else result.stderr
        
        return ToolResult(
            success=success,
            output=output_payload,
            error=result.stderr if not success else None,
            metadata={"exit_code": result.exit_code}
        )