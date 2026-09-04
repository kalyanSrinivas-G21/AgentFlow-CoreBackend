# backend/app/tools/filesystem_tools.py
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from app.tools.base import Tool, register_tool
from app.workspace.service import WorkspaceService

class WriteInput(BaseModel):
    path: str = Field(..., description="Relative path to write the file")
    content: str = Field(..., description="Content of the file")

@register_tool
class FilesystemWriteTool(Tool):
    name = "filesystem.write"
    input_schema = WriteInput
    timeout_s = 5.0
    retryable = True

    async def run(self, args: Dict[str, Any], project_id: str) -> str:
        parsed = self.input_schema(**args)
        target = WorkspaceService.resolve_path(project_id, parsed.path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(parsed.content, encoding="utf-8")
        return f"Successfully wrote {len(parsed.content)} bytes to {parsed.path}"

class ReadInput(BaseModel):
    path: str = Field(..., description="Relative path to read from")

@register_tool
class FilesystemReadTool(Tool):
    name = "filesystem.read"
    input_schema = ReadInput
    timeout_s = 5.0
    retryable = True

    async def run(self, args: Dict[str, Any], project_id: str) -> str:
        parsed = self.input_schema(**args)
        target = WorkspaceService.resolve_path(project_id, parsed.path)
        if not target.is_file():
            raise FileNotFoundError(f"File not found: {parsed.path}")
        return target.read_text(encoding="utf-8")

class ListInput(BaseModel):
    path: str = Field(..., description="Relative directory path to list")

@register_tool
class FilesystemListTool(Tool):
    name = "filesystem.list"
    input_schema = ListInput
    timeout_s = 5.0
    retryable = True

    async def run(self, args: Dict[str, Any], project_id: str) -> List[str]:
        parsed = self.input_schema(**args)
        target = WorkspaceService.resolve_path(project_id, parsed.path)
        if not target.is_dir():
            raise NotADirectoryError(f"Directory not found: {parsed.path}")
        return [p.name for p in target.iterdir()]