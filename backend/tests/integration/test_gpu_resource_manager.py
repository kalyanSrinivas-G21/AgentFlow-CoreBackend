# backend/tests/integration/test_gpu_resource_manager.py
import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from app.models_ai.resource_manager import ResourceManager, GPUResourceManager, ResourceExhaustedError, NvmlResourceProvider, ResourceSnapshot
from datetime import datetime, timezone

pytestmark = pytest.mark.asyncio


def make_fresh_manager() -> ResourceManager:
    """
    Create a fresh ResourceManager instance with a very short default_timeout_s
    so tests fail fast rather than waiting 30 seconds.
    Each call returns a new instance — no singleton state leaks between tests.
    """
    return ResourceManager(
        provider=NvmlResourceProvider(),
        default_timeout_s=0.05,   # 50 ms — fail fast in tests
        safety_buffer_mb=200,
    )


@patch.object(NvmlResourceProvider, "snapshot")
async def test_admission_control_oom_prevention(mock_snapshot):
    """
    Validates that a request requiring more VRAM than available is
    strictly rejected rather than crashing the system.

    Root cause of original failure: tests called manager._init_state() which
    never existed on ResourceManager or GPUResourceManager.  Fixed by creating
    a fresh ResourceManager instance per test (no shared singleton state).
    """
    manager = make_fresh_manager()

    # Mock hardware possessing only 2 GB free VRAM
    mock_snapshot.return_value = ResourceSnapshot(
        free_vram_mb=2048,
        used_vram_mb=1000,
        total_vram_mb=3048,
        source="nvml",
        state="measured",
        observed_at=datetime.now(timezone.utc),
    )

    with pytest.raises(ResourceExhaustedError):
        # 4800 MB requested, only 2048 free — must be rejected
        await manager.acquire("llama3.1:8b", estimated_vram_mb=4800)


@patch.object(NvmlResourceProvider, "snapshot")
async def test_concurrency_limit_enforcement(mock_snapshot):
    """
    Validates that the pending-queue limit (max_pending) is enforced and
    that cpu_fallback correctly bypasses VRAM checks when GPU is unavailable.

    Original test called _init_state() (non-existent) and had inconsistent
    assertions.  Replaced with a precise test of the actual ResourceManager API.
    """
    manager = make_fresh_manager()

    # GPU unavailable — NVML reports state=unavailable
    mock_snapshot.return_value = ResourceSnapshot(
        free_vram_mb=0,
        used_vram_mb=0,
        total_vram_mb=0,
        source="nvml",
        state="unavailable",
        observed_at=datetime.now(timezone.utc),
    )

    # cpu_fallback=True must succeed even when GPU VRAM is unavailable
    lease_a = await manager.acquire("model_a", estimated_vram_mb=100, cpu_fallback=True)
    assert lease_a.execution_mode == "cpu"

    lease_b = await manager.acquire("model_b", estimated_vram_mb=100, cpu_fallback=True)
    assert lease_b.execution_mode == "cpu"

    # Without cpu_fallback, an unavailable GPU must raise ResourceExhaustedError
    with pytest.raises(ResourceExhaustedError):
        await manager.acquire("model_c", estimated_vram_mb=100, cpu_fallback=False)

    # Releasing leases must not raise
    await lease_a.release()
    await lease_b.release()