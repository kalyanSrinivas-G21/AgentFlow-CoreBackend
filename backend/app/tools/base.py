from abc import ABC, abstractmethod
from typing import Dict, Any, Type
from pydantic import BaseModel

# In-memory registry mapping tool names to Tool instances
TOOL_REGISTRY: Dict[str, "Tool"] = {}

class Tool(ABC):
    name: str
    input_schema: Type[BaseModel]
    timeout_s: float = 10.0
    retryable: bool = False

    @abstractmethod
    async def run(self, args: Dict[str, Any], project_id: str, db=None) -> Any:
        pass

def register_tool(cls):
    """Decorator to instantiate and register a tool into the global registry."""
    instance = cls()
    TOOL_REGISTRY[instance.name] = instance
    return cls