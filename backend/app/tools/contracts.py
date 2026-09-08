from abc import ABC, abstractmethod
from typing import Any, Literal, Optional, Type

from pydantic import BaseModel, Field

ToolHealth = Literal["available", "busy", "degraded", "unavailable", "failed"]
PermissionLevel = Literal["read", "write", "execute", "privileged"]
ExecutionEnvironment = Literal["backend", "sandbox", "worker"]


class ToolDefinition(BaseModel):
    """Validated metadata presented to planners and enforced by the executor."""

    tool_id: str
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    permission_level: PermissionLevel
    execution_environment: ExecutionEnvironment
    timeout_seconds: float = Field(gt=0)
    resource_limits: dict[str, Any] = Field(default_factory=dict)
    network_policy: dict[str, Any] = Field(default_factory=dict)
    supported_task_types: list[str] = Field(default_factory=list)
    health: ToolHealth
    requires_approval: bool = False


class ToolRegistry(ABC):
    """Single metadata and lookup boundary for all agent-invokable tools."""

    @abstractmethod
    async def register(self, definition: ToolDefinition) -> ToolDefinition:
        raise NotImplementedError

    @abstractmethod
    async def get(self, tool_id: str) -> Optional[ToolDefinition]:
        raise NotImplementedError

    @abstractmethod
    async def list(self, task_type: Optional[str] = None) -> list[ToolDefinition]:
        raise NotImplementedError

    @abstractmethod
    async def validate_input(self, tool_id: str, arguments: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class ToolExecutor(ABC):
    """Execution boundary that future orchestration must use after registry validation."""

    @abstractmethod
    async def execute(
        self,
        tool_id: str,
        arguments: dict[str, Any],
        project_id: str,
        task_id: str,
    ) -> dict[str, Any]:
        raise NotImplementedError
