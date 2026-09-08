import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional

from pydantic import BaseModel, Field

try:
    import pynvml
except ImportError:  # pragma: no cover - dependency availability is platform-specific
    pynvml = None

logger = logging.getLogger(__name__)


class ResourceExhaustedError(Exception):
    """Raised when a bounded local resource path cannot admit a request."""


class EvictionDeferredError(Exception):
    """Raised when a model has active requests and cannot be unloaded safely."""


class ResourceSnapshot(BaseModel):
    total_vram_mb: Optional[int] = Field(default=None, ge=0)
    used_vram_mb: Optional[int] = Field(default=None, ge=0)
    free_vram_mb: Optional[int] = Field(default=None, ge=0)
    source: str
    state: str
    observed_at: datetime
    per_model_vram_mb: Optional[dict[str, int]] = None


class ResourceProvider(ABC):
    @abstractmethod
    async def snapshot(self) -> ResourceSnapshot:
        raise NotImplementedError


class NvmlResourceProvider(ResourceProvider):
    """Real NVML provider; unsupported or unavailable VRAM stays explicitly unmeasured."""

    def __init__(self, device_index: int = 0):
        self.device_index = device_index
        self._initialized = False
        if pynvml is not None:
            try:
                pynvml.nvmlInit()
                self._initialized = True
            except Exception as exc:
                logger.info("NVML unavailable: %s", exc)

    async def snapshot(self) -> ResourceSnapshot:
        now = datetime.now(timezone.utc)
        if not self._initialized:
            return ResourceSnapshot(source="nvml", state="unavailable", observed_at=now)
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(self.device_index)
            info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            megabyte = 1024 * 1024
            return ResourceSnapshot(
                total_vram_mb=info.total // megabyte,
                used_vram_mb=info.used // megabyte,
                free_vram_mb=info.free // megabyte,
                source="nvml",
                state="measured",
                observed_at=now,
            )
        except Exception as exc:
            logger.warning("NVML snapshot failed: %s", exc)
            return ResourceSnapshot(source="nvml", state="unavailable", observed_at=now)


@dataclass
class _LoadedModel:
    estimated_vram_mb: int
    active_requests: int = 0
    execution_mode: str = "gpu"


@dataclass
class ModelLease:
    manager: "ResourceManager"
    model_id: str
    execution_mode: str
    _released: bool = False

    async def release(self) -> None:
        if not self._released:
            self._released = True
            await self.manager.release(self.model_id)

    async def __aenter__(self) -> "ModelLease":
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        await self.release()


class ResourceManager:
    """Bounded async admission controller with active-request-safe eviction."""

    def __init__(
        self,
        provider: Optional[ResourceProvider] = None,
        max_pending: int = 8,
        safety_buffer_mb: int = 200,
        default_timeout_s: float = 30.0,
        unload_callback: Optional[Callable[[str], Awaitable[None]]] = None,
    ):
        self.provider = provider or NvmlResourceProvider()
        self.max_pending = max_pending
        self.safety_buffer_mb = safety_buffer_mb
        self.default_timeout_s = default_timeout_s
        self.unload_callback = unload_callback
        self._condition = asyncio.Condition()
        self._loaded: dict[str, _LoadedModel] = {}
        self._pending = 0

    async def snapshot(self) -> ResourceSnapshot:
        return await self.provider.snapshot()

    async def acquire(
        self,
        model_id: str,
        estimated_vram_mb: int,
        *,
        cpu_fallback: bool = False,
        timeout_s: Optional[float] = None,
    ) -> ModelLease:
        if estimated_vram_mb < 0:
            raise ValueError("estimated_vram_mb must not be negative")
        deadline = asyncio.get_running_loop().time() + (timeout_s if timeout_s is not None else self.default_timeout_s)
        async with self._condition:
            if model_id in self._loaded:
                record = self._loaded[model_id]
                record.active_requests += 1
                return ModelLease(self, model_id, record.execution_mode)
            if self._pending >= self.max_pending:
                raise ResourceExhaustedError("Model swap queue is full")
            self._pending += 1
            try:
                while True:
                    snapshot = await self.provider.snapshot()
                    if snapshot.state == "unavailable":
                        if cpu_fallback:
                            self._loaded[model_id] = _LoadedModel(estimated_vram_mb, 1, "cpu")
                            return ModelLease(self, model_id, "cpu")
                        raise ResourceExhaustedError(
                            f"VRAM is unavailable; model {model_id} has no declared CPU fallback"
                        )
                    available = snapshot.free_vram_mb or 0
                    if available >= estimated_vram_mb + self.safety_buffer_mb:
                        self._loaded[model_id] = _LoadedModel(estimated_vram_mb, 1, "gpu")
                        return ModelLease(self, model_id, "gpu")
                    idle_model = next(
                        (name for name, record in self._loaded.items() if record.active_requests == 0),
                        None,
                    )
                    if idle_model is not None:
                        await self._evict_idle_locked(idle_model)
                        continue
                    remaining = deadline - asyncio.get_running_loop().time()
                    if remaining <= 0:
                        if cpu_fallback:
                            self._loaded[model_id] = _LoadedModel(estimated_vram_mb, 1, "cpu")
                            return ModelLease(self, model_id, "cpu")
                        raise ResourceExhaustedError(
                            f"Insufficient measured VRAM for {model_id}; request rejected safely"
                        )
                    try:
                        await asyncio.wait_for(self._condition.wait(), timeout=remaining)
                    except asyncio.TimeoutError as exc:
                        if cpu_fallback:
                            self._loaded[model_id] = _LoadedModel(estimated_vram_mb, 1, "cpu")
                            return ModelLease(self, model_id, "cpu")
                        raise ResourceExhaustedError(
                            f"Timed out waiting for VRAM for {model_id}"
                        ) from exc
            finally:
                self._pending -= 1

    async def _evict_idle_locked(self, model_id: str) -> None:
        record = self._loaded.get(model_id)
        if record is None:
            return
        if record.active_requests:
            raise EvictionDeferredError(f"Model {model_id} is serving active requests")
        if self.unload_callback is not None:
            await self.unload_callback(model_id)
        del self._loaded[model_id]
        self._condition.notify_all()

    async def evict(self, model_id: str) -> None:
        async with self._condition:
            record = self._loaded.get(model_id)
            if record is None:
                return
            if record.active_requests:
                raise EvictionDeferredError(f"Model {model_id} is serving active requests")
            await self._evict_idle_locked(model_id)

    async def release(self, model_id: str) -> None:
        async with self._condition:
            record = self._loaded.get(model_id)
            if record is None:
                return
            record.active_requests = max(0, record.active_requests - 1)
            self._condition.notify_all()

    async def lease(self, model_id: str, estimated_vram_mb: int, *, cpu_fallback: bool = False, timeout_s: Optional[float] = None) -> ModelLease:
        return await self.acquire(
            model_id,
            estimated_vram_mb,
            cpu_fallback=cpu_fallback,
            timeout_s=timeout_s,
        )

    async def active_request_count(self, model_id: str) -> int:
        async with self._condition:
            return self._loaded.get(model_id, _LoadedModel(0)).active_requests


class GPUResourceManager(ResourceManager):
    """Compatibility facade for the existing Ollama provider admission calls."""

    def __init__(self):
        super().__init__(default_timeout_s=0.1)
        self._legacy_models: list[str] = []

    async def admit(self, model_id: str, base_url: str) -> None:
        from app.models_ai.registry import get_model

        descriptor = get_model(model_id)
        if descriptor is None:
            raise ResourceExhaustedError(f"Unknown model {model_id}; no safe resource estimate is available")
        # cpu_fallback=True: if GPU is unavailable (no NVML, no VRAM) the model
        # still runs on CPU via Ollama — sovereign local execution still satisfied.
        await self.acquire(model_id, descriptor.estimated_vram_mb, cpu_fallback=True)
        self._legacy_models.append(model_id)

    async def release(self) -> None:
        if self._legacy_models:
            await super().release(self._legacy_models.pop())

    def get_hardware_telemetry(self):
        """Deprecated sync compatibility view; unavailable fields remain None."""
        if not isinstance(self.provider, NvmlResourceProvider) or not self.provider._initialized:
            return {"gpu_available": False, "free_vram_mb": None, "used_vram_mb": None, "total_vram_mb": None, "state": "unavailable"}
        return {"gpu_available": True, "state": "measured"}
