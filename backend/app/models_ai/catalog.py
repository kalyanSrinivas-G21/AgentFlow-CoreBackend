from typing import Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models_ai.contracts import ModelCatalog, ModelCatalogEntry, ModelHealth, ModelStatus
from app.models_ai.registry_model import ModelRegistryEntry


class InMemoryModelCatalog(ModelCatalog):
    """Deterministic catalog double for unit tests and local contract probes."""

    def __init__(self, entries: Optional[list[ModelCatalogEntry]] = None):
        self._entries = {entry.model_id: entry for entry in entries or []}

    async def get(self, model_id: str) -> Optional[ModelCatalogEntry]:
        return self._entries.get(model_id)

    async def list(self, capability: Optional[str] = None) -> list[ModelCatalogEntry]:
        entries = list(self._entries.values())
        if capability is not None:
            entries = [entry for entry in entries if capability in entry.capabilities]
        return entries

    async def register(self, model: ModelCatalogEntry) -> ModelCatalogEntry:
        self._entries[model.model_id] = model
        return model

    async def update_status(self, model_id: str, status: ModelStatus) -> ModelCatalogEntry:
        entry = self._entries[model_id]
        updated = entry.model_copy(update={"status": status})
        self._entries[model_id] = updated
        return updated


class SqlAlchemyModelCatalog(ModelCatalog):
    """Persistent catalog backed by the restored PostgreSQL model_registry table."""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _to_entry(row: ModelRegistryEntry) -> ModelCatalogEntry:
        status = ModelStatus(
            availability=row.availability,
            load_state=row.load_state,
            health=row.health,
            updated_at=row.last_checked_at,
            failure_reason=row.failure_reason,
        )
        return ModelCatalogEntry(
            model_id=row.model_id,
            display_name=row.display_name,
            provider_type=row.provider_type,
            runtime_type=row.runtime_type,
            location=row.location,
            capabilities=row.capabilities or [],
            modalities=row.modalities or [],
            context_limit=row.context_limit,
            estimated_vram_mb=row.estimated_vram_mb,
            measured_vram_mb=row.measured_vram_mb,
            cpu_fallback=row.cpu_fallback,
            gpu_required=row.gpu_required,
            supported_devices=row.supported_devices or [],
            version=row.version,
            configuration=row.configuration or {},
            status=status,
        )

    @staticmethod
    def _from_entry(model: ModelCatalogEntry) -> ModelRegistryEntry:
        return ModelRegistryEntry(
            id=uuid4(),
            model_id=model.model_id,
            display_name=model.display_name,
            provider_type=model.provider_type,
            runtime_type=model.runtime_type,
            location=model.location,
            capabilities=model.capabilities,
            modalities=model.modalities,
            context_limit=model.context_limit,
            estimated_vram_mb=model.estimated_vram_mb,
            measured_vram_mb=model.measured_vram_mb,
            cpu_fallback=model.cpu_fallback,
            gpu_required=model.gpu_required,
            supported_devices=model.supported_devices,
            version=model.version,
            configuration=model.configuration,
            availability=model.status.availability,
            load_state=model.status.load_state,
            health=model.status.health,
            failure_reason=model.status.failure_reason,
        )

    async def get(self, model_id: str) -> Optional[ModelCatalogEntry]:
        row = await self.db.scalar(select(ModelRegistryEntry).where(ModelRegistryEntry.model_id == model_id))
        return self._to_entry(row) if row else None

    async def list(self, capability: Optional[str] = None) -> list[ModelCatalogEntry]:
        rows = list((await self.db.scalars(select(ModelRegistryEntry))).all())
        entries = [self._to_entry(row) for row in rows]
        return [entry for entry in entries if capability is None or capability in entry.capabilities]

    async def register(self, model: ModelCatalogEntry) -> ModelCatalogEntry:
        row = self._from_entry(model)
        self.db.add(row)
        await self.db.flush()
        return self._to_entry(row)

    async def update_status(self, model_id: str, status: ModelStatus) -> ModelCatalogEntry:
        row = await self.db.scalar(select(ModelRegistryEntry).where(ModelRegistryEntry.model_id == model_id))
        if row is None:
            raise KeyError(f"Unknown model: {model_id}")
        row.availability = status.availability
        row.load_state = status.load_state
        row.health = status.health
        row.failure_reason = status.failure_reason
        await self.db.flush()
        return self._to_entry(row)
