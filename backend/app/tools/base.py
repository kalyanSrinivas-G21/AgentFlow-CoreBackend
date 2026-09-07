# backend/app/tools/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Type, List
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.tools.models import ToolResult

# In-memory registry mapping tool names to Tool instances
TOOL_REGISTRY: Dict[str, "Tool"] = {}

class Tool(ABC):
    name: str
    description: str = "No description provided."
    input_schema: Type[BaseModel]
    timeout_s: float = 10.0
    retryable: bool = False

    @abstractmethod
    async def run(self, args: Dict[str, Any], project_id: str, db: AsyncSession = None) -> ToolResult:
        pass

def register_tool(cls):
    """Decorator to instantiate and register a tool into the global registry."""
    instance = cls()
    TOOL_REGISTRY[instance.name] = instance
    return cls

def get_tool_catalog() -> List[Dict[str, Any]]:
    """Generates a JSON schema representation of all registered tools for the LLM planner."""
    catalog = []
    for name, tool in TOOL_REGISTRY.items():
        catalog.append({
            "name": tool.name,
            "description": getattr(tool, 'description', f"Executes {tool.name}"),
            "parameters": tool.input_schema.model_json_schema()
        })
    return catalog

def init_tools():
    """Explicitly register all tools to prevent import-order bugs."""
    import app.tools.filesystem_tools
    import app.tools.code_tools
    import app.tools.document_tools