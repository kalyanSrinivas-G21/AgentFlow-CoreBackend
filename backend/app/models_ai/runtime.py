from datetime import datetime, timezone
from typing import AsyncIterator

from app.models_ai.contracts import ModelCatalogEntry, ModelInferenceRequest, ModelResourceUsage, ModelRuntime, ModelStatus
from app.models_ai.ollama_provider import OllamaProvider


class OllamaRuntime(ModelRuntime):
    """Provider adapter that keeps all inference on the audited Ollama path."""

    def __init__(self, provider: OllamaProvider | None = None):
        self.provider = provider or OllamaProvider()

    async def load_model(self, model: ModelCatalogEntry) -> ModelStatus:
        return ModelStatus(
            availability=True,
            load_state="loaded",
            health="idle",
            updated_at=datetime.now(timezone.utc),
        )

    async def unload_model(self, model_id: str) -> ModelStatus:
        return ModelStatus(
            availability=True,
            load_state="unloaded",
            health="available",
            updated_at=datetime.now(timezone.utc),
        )

    async def check_model_status(self, model_id: str) -> ModelStatus:
        return await self.health_check(model_id)

    async def run_inference(self, request: ModelInferenceRequest) -> str:
        return await self.provider.generate(
            request.model_id,
            request.prompt,
            system=request.system,
            options=request.options,
        )

    async def embed(self, model_id: str, text: str) -> list[float]:
        return await self.provider.embed(model_id, text)

    async def stream_inference(self, request: ModelInferenceRequest) -> AsyncIterator[str]:
        async for chunk in self.provider.stream(request.model_id, request.prompt, request.system):
            yield chunk

    async def get_resource_usage(self, model_id: str) -> ModelResourceUsage:
        return ModelResourceUsage(
            model_id=model_id,
            used_vram_mb=None,
            available_vram_mb=None,
            source="runtime_not_measured",
            observed_at=datetime.now(timezone.utc),
        )

    async def health_check(self, model_id: str) -> ModelStatus:
        return ModelStatus(
            availability=True,
            load_state="unloaded",
            health="available",
            updated_at=datetime.now(timezone.utc),
        )
