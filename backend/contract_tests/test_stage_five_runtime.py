import asyncio
from datetime import datetime, timezone

import pytest

from app.models_ai.catalog import InMemoryModelCatalog
from app.models_ai.contracts import ModelCatalogEntry, ModelInferenceRequest
from app.models_ai.resource_manager import (
    EvictionDeferredError,
    ResourceExhaustedError,
    ResourceManager,
    ResourceProvider,
    ResourceSnapshot,
)
from app.models_ai.router_v2 import ModelRouter
from app.models_ai.runtime import OllamaRuntime
from app.models_ai.ollama_provider import OllamaProvider
from app.security.application_auditor import ApplicationTelemetryAuditor
from app.security.sovereignty import TrustedNetworkPolicy


class FixedResourceProvider(ResourceProvider):
    def __init__(self, snapshot: ResourceSnapshot):
        self.current = snapshot

    async def snapshot(self) -> ResourceSnapshot:
        return self.current


class FakeRuntime:
    async def run_inference(self, request):
        return f"ran:{request.model_id}"


def entry(model_id="local-general", *, capability="general", vram=100, health="available", cpu_fallback=False):
    return ModelCatalogEntry(
        model_id=model_id,
        display_name=model_id,
        provider_type="ollama",
        runtime_type="ollama",
        location="http://ollama:11434",
        capabilities=[capability],
        modalities=["text"],
        estimated_vram_mb=vram,
        cpu_fallback=cpu_fallback,
        gpu_required=not cpu_fallback,
        status={
            "availability": health not in {"unavailable", "failed"},
            "load_state": "unloaded",
            "health": health,
            "updated_at": datetime.now(timezone.utc),
        },
    )


def measured_snapshot(free=2048):
    return ResourceSnapshot(
        total_vram_mb=4096,
        used_vram_mb=4096 - free,
        free_vram_mb=free,
        source="test-measured-provider",
        state="measured",
        observed_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_catalog_router_skips_unavailable_model():
    catalog = InMemoryModelCatalog([entry("failed", health="failed"), entry("healthy")])
    router = ModelRouter(catalog=catalog)

    selected = await router.select(["general"])

    assert selected.model_id == "healthy"


@pytest.mark.asyncio
async def test_gpu_oom_shaped_path_rejects_without_cloud_fallback():
    manager = ResourceManager(
        provider=FixedResourceProvider(measured_snapshot(free=100)),
        safety_buffer_mb=50,
        default_timeout_s=0,
    )

    with pytest.raises(ResourceExhaustedError, match="Insufficient measured VRAM"):
        await manager.acquire("large-local-model", 500, timeout_s=0)

    snapshot = await manager.snapshot()
    assert snapshot.state == "measured"
    assert snapshot.free_vram_mb == 100


@pytest.mark.asyncio
async def test_unavailable_vram_is_not_presented_as_zero():
    unavailable = ResourceSnapshot(
        source="nvml",
        state="unavailable",
        observed_at=datetime.now(timezone.utc),
    )
    manager = ResourceManager(provider=FixedResourceProvider(unavailable))

    snapshot = await manager.snapshot()

    assert snapshot.state == "unavailable"
    assert snapshot.free_vram_mb is None
    assert snapshot.used_vram_mb is None


@pytest.mark.asyncio
async def test_eviction_is_deferred_during_slow_inference():
    manager = ResourceManager(provider=FixedResourceProvider(measured_snapshot()))
    started = asyncio.Event()
    finish = asyncio.Event()

    async def slow_inference():
        async with await manager.lease("slow-model", 100):
            started.set()
            await finish.wait()

    task = asyncio.create_task(slow_inference())
    await started.wait()

    with pytest.raises(EvictionDeferredError, match="active requests"):
        await manager.evict("slow-model")

    finish.set()
    await task
    await manager.evict("slow-model")
    assert await manager.active_request_count("slow-model") == 0


@pytest.mark.asyncio
async def test_router_initiated_ollama_request_is_visible_to_auditor():
    auditor = ApplicationTelemetryAuditor(
        policy=TrustedNetworkPolicy(local_ai_services=["ollama"], default_external_decision="blocked")
    )
    provider = OllamaProvider(base_url="http://ollama:11434")

    async def audited_generate(model, prompt, system=None, options=None):
        await auditor.record_request(
            provider.base_url,
            source_component="ollama_provider",
            request_classification="local_ai_inference",
        )
        return "local result"

    provider.generate = audited_generate
    runtime = OllamaRuntime(provider=provider)
    catalog = InMemoryModelCatalog([entry()])
    manager = ResourceManager(provider=FixedResourceProvider(measured_snapshot()))
    router = ModelRouter(catalog=catalog, resource_manager=manager, runtime=runtime)

    result = await router.run(
        ModelInferenceRequest(model_id="auto", prompt="local prompt"),
        ["general"],
    )

    metrics = await auditor.metrics()
    assert result == "local result"
    assert metrics.local_ai_request_count == 1
    assert metrics.recent_events[-1].source_component == "ollama_provider"
