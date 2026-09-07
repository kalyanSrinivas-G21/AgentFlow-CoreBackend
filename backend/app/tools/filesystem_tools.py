# backend/app/tools/filesystem_tools.py
from typing import Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.tools.base import Tool, register_tool
from app.tools.models import ToolResult
from app.workspace.service import WorkspaceService

class WriteInput(BaseModel):
    path: str = Field(..., description="Relative path to write the file")
    content: str = Field(..., description="Content of the file")

@register_tool
class FilesystemWriteTool(Tool):
    name = "filesystem.write"
    description = "Writes text content to a file in the project workspace."
    input_schema = WriteInput
    timeout_s = 5.0
    retryable = True

    async def run(self, args: Dict[str, Any], project_id: str, db: AsyncSession = None) -> ToolResult:
        # Args are pre-validated by Executor Stage 3
        target = WorkspaceService.resolve_path(project_id, args["path"])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(args["content"], encoding="utf-8")
        
        return ToolResult(
            success=True, 
            output=f"Successfully wrote {len(args['content'])} bytes.",
            metadata={"path": args["path"], "bytes": len(args["content"])}
        )

class ReadInput(BaseModel):
    path: str = Field(..., description="Relative path to read from")

@register_tool
class FilesystemReadTool(Tool):
    name = "filesystem.read"
    description = "Reads text content from a file in the project workspace."
    input_schema = ReadInput
    timeout_s = 5.0
    retryable = True

    async def run(self, args: Dict[str, Any], project_id: str, db: AsyncSession = None) -> ToolResult:
        target = WorkspaceService.resolve_path(project_id, args["path"])
        if not target.is_file():
            return ToolResult(success=False, error=f"File not found: {args['path']}")
        
        content = target.read_text(encoding="utf-8")
        return ToolResult(success=True, output=content, metadata={"length": len(content)})

class ListInput(BaseModel):
    path: str = Field(..., description="Relative directory path to list")

@register_tool
class FilesystemListTool(Tool):
    name = "filesystem.list"
    description = "Lists files and directories in the project workspace."
    input_schema = ListInput
    timeout_s = 5.0
    retryable = True

    async def run(self, args: Dict[str, Any], project_id: str, db: AsyncSession = None) -> ToolResult:
        target = WorkspaceService.resolve_path(project_id, args["path"])
        if not target.is_dir():
            return ToolResult(success=False, error=f"Directory not found: {args['path']}")
            
        items = [p.name for p in target.iterdir()]
        return ToolResult(success=True, output="\n".join(items), metadata={"count": len(items)})