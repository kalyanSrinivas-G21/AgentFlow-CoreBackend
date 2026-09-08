from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, AsyncIterator, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

ModelHealth = Literal[
    "available",
    "loading",
    "loaded",
    "busy",
    "idle",
    "unloading",
    "unavailable",
    "failed",
    "degraded",
]
LoadState = Literal["unloaded", "loading", "loaded", "unloading"]


class ModelStatus(BaseModel):
    availability: bool
    load_state: LoadState
    health: ModelHealth
    updated_at: datetime
    failure_reason: Optional[str] = None


class ModelCatalogEntry(BaseModel):
    """Persistent catalog metadata used for capability-aware local routing."""

    model_id: str
    display_name: str
    provider_type: str
    runtime_type: str
    location: str
    capabilities: list[str] = Field(default_factory=list)
    modalities: list[str] = Field(default_factory=list)
    context_limit: Optional[int] = Field(default=None, gt=0)
    estimated_vram_mb: Optional[int] = Field(default=None, ge=0)
    measured_vram_mb: Optional[int] = Field(default=None, ge=0)
    cpu_fallback: bool = False
    gpu_required: bool = False
    supported_devices: list[str] = Field(default_factory=list)
    version: Optional[str] = None
    configuration: dict[str, Any] = Field(default_factory=dict)
    status: ModelStatus


class ModelCatalog(ABC):
    """Persistent registry boundary for model metadata and current status."""

    @abstractmethod
    async def get(self, model_id: str) -> Optional[ModelCatalogEntry]:
        raise NotImplementedError

    @abstractmethod
    async def list(self, capability: Optional[str] = None) -> list[ModelCatalogEntry]:
        raise NotImplementedError

    @abstractmethod
    async def register(self, model: ModelCatalogEntry) -> ModelCatalogEntry:
        raise NotImplementedError

    @abstractmethod
    async def update_status(self, model_id: str, status: ModelStatus) -> ModelCatalogEntry:
        raise NotImplementedError


class ModelInferenceRequest(BaseModel):
    model_id: str
    prompt: str
    system: Optional[str] = None
    options: dict[str, Any] = Field(default_factory=dict)
    task_id: Optional[UUID] = None
    execution_id: Optional[UUID] = None


class ModelResourceUsage(BaseModel):
    model_id: str
    used_vram_mb: Optional[int] = Field(default=None, ge=0)
    available_vram_mb: Optional[int] = Field(default=None, ge=0)
    source: str
    observed_at: datetime


class ModelRuntime(ABC):
    """Provider-neutral contract for local model lifecycle and inference."""

    @abstractmethod
    async def load_model(self, model: ModelCatalogEntry) -> ModelStatus:
        raise NotImplementedError

    @abstractmethod
    async def unload_model(self, model_id: str) -> ModelStatus:
        raise NotImplementedError

    @abstractmethod
    async def check_model_status(self, model_id: str) -> ModelStatus:
        raise NotImplementedError

    @abstractmethod
    async def run_inference(self, request: ModelInferenceRequest) -> str:
        raise NotImplementedError

    @abstractmethod
    async def embed(self, model_id: str, text: str) -> list[float]:
        raise NotImplementedError

    @abstractmethod
    async def stream_inference(self, request: ModelInferenceRequest) -> AsyncIterator[str]:
        raise NotImplementedError

    @abstractmethod
    async def get_resource_usage(self, model_id: str) -> ModelResourceUsage:
        raise NotImplementedError

    @abstractmethod
    async def health_check(self, model_id: str) -> ModelStatus:
        raise NotImplementedError
