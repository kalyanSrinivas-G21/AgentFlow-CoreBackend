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
    tool_id: str
    description: str = "No description provided."
    input_schema: Type[BaseModel]
    timeout_s: float = 10.0
    retryable: bool = False
    permission_level: str = "execute"
    execution_environment: str = "backend"
    resource_limits: Dict[str, Any] = {}
    network_policy: Dict[str, Any] = {"default": "blocked"}
    supported_task_types: List[str] = []
    health: str = "available"
    requires_approval: bool = False

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
            "tool_id": getattr(tool, "tool_id", name),
            "name": tool.name,
            "description": getattr(tool, 'description', f"Executes {tool.name}"),
            "parameters": tool.input_schema.model_json_schema(),
            "permission_level": tool.permission_level,
            "execution_environment": tool.execution_environment,
            "timeout_seconds": tool.timeout_s,
            "resource_limits": tool.resource_limits,
            "network_policy": tool.network_policy,
            "supported_task_types": tool.supported_task_types,
            "health": tool.health,
            "requires_approval": tool.requires_approval,
        })
    return catalog

def init_tools():
    """Explicitly register all tools to prevent import-order bugs."""
    import app.tools.filesystem_tools
    import app.tools.code_tools
    import app.tools.document_tools