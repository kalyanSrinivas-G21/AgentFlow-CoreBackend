from datetime import datetime, timezone
from typing import Optional

from app.models_ai.catalog import InMemoryModelCatalog
from app.models_ai.contracts import ModelCatalog, ModelCatalogEntry, ModelInferenceRequest, ModelRuntime
from app.models_ai.registry import list_models
from app.models_ai.resource_manager import ResourceManager


def default_catalog() -> InMemoryModelCatalog:
    entries = []
    for descriptor in list_models():
        entries.append(
            ModelCatalogEntry(
                model_id=descriptor.model_id,
                display_name=descriptor.model_id,
                provider_type=descriptor.provider,
                runtime_type=descriptor.provider,
                location="configured_local_runtime",
                capabilities=descriptor.capabilities,
                modalities=["text"],
                context_limit=descriptor.context_length,
                estimated_vram_mb=descriptor.estimated_vram_mb,
                cpu_fallback=False,
                gpu_required=True,
                supported_devices=["cuda"],
                status={
                    "availability": True,
                    "load_state": "unloaded",
                    "health": "available",
                    "updated_at": datetime.now(timezone.utc),
                },
            )
        )
    return InMemoryModelCatalog(entries)


class ModelRouter:
    """Capability, health, and resource-aware local model router."""

    def __init__(
        self,
        catalog: Optional[ModelCatalog] = None,
        resource_manager: Optional[ResourceManager] = None,
        runtime: Optional[ModelRuntime] = None,
    ):
        self.catalog = catalog or default_catalog()
        self.resource_manager = resource_manager
        self.runtime = runtime

    async def select(
        self,
        required_capabilities: list[str],
        *,
        modality: Optional[str] = None,
        explicit_model: Optional[str] = None,
    ) -> ModelCatalogEntry:
        candidates = await self.catalog.list()
        if explicit_model and explicit_model != "auto":
            candidates = [entry for entry in candidates if entry.model_id == explicit_model]
        for candidate in candidates:
            if not candidate.status.availability or candidate.status.health in {"unavailable", "failed"}:
                continue
            if not all(capability in candidate.capabilities for capability in required_capabilities):
                continue
            if modality and modality not in candidate.modalities:
                continue
            return candidate
        raise ValueError(f"No registered model satisfies capabilities: {required_capabilities}")

    async def run(self, request: ModelInferenceRequest, required_capabilities: list[str]) -> str:
        if self.runtime is None or self.resource_manager is None:
            raise RuntimeError("ModelRouter requires a runtime and ResourceManager for inference")
        selected = await self.select(required_capabilities, explicit_model=request.model_id)
        if selected.estimated_vram_mb is None:
            raise RuntimeError(f"Model {selected.model_id} has no safe VRAM estimate")
        async with await self.resource_manager.lease(
            selected.model_id,
            selected.estimated_vram_mb,
            cpu_fallback=selected.cpu_fallback,
        ):
            return await self.runtime.run_inference(request.model_copy(update={"model_id": selected.model_id}))

    def route(self, explicit_model: Optional[str] = None, required_capabilities: Optional[list[str]] = None) -> str:
        """Legacy synchronous selector retained until orchestration migrates to select()."""
        required_capabilities = required_capabilities or ["general"]
        if not isinstance(self.catalog, InMemoryModelCatalog):
            raise RuntimeError("Synchronous route is unavailable for a persistent catalog")
        for entry in awaitable_entries(self.catalog):
            if explicit_model and explicit_model != "auto" and entry.model_id != explicit_model:
                continue
            if entry.status.availability and entry.status.health not in {"unavailable", "failed"} and all(capability in entry.capabilities for capability in required_capabilities):
                return entry.model_id
        raise ValueError(f"No registered model satisfies capabilities: {required_capabilities}")

    def get_embedding_model(self) -> str:
        return self.route(required_capabilities=["embedding"])


def awaitable_entries(catalog: InMemoryModelCatalog) -> list[ModelCatalogEntry]:
    return list(catalog._entries.values())
