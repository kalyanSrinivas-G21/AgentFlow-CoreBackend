# backend/tests/integration/test_gpu_resource_manager.py
import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from app.models_ai.resource_manager import GPUResourceManager, ResourceExhaustedError

pytestmark = pytest.mark.asyncio

@patch("app.models_ai.resource_manager.get_model")
@patch.object(GPUResourceManager, "get_hardware_telemetry")
async def test_admission_control_oom_prevention(mock_telemetry, mock_get_model):
    """
    Validates that a request requiring more VRAM than available is 
    strictly rejected (queued) rather than crashing the system.
    """
    # Reset singleton state for test isolation
    manager = GPUResourceManager()
    manager._init_state()
    
    # Mock hardware possessing only 2GB free VRAM
    mock_telemetry.return_value = {
        "gpu_available": True,
        "free_vram_mb": 2048,
        "used_vram_mb": 1000,
        "total_vram_mb": 3048
    }
    
    # Mock model descriptor requesting 4.8GB VRAM (e.g., Llama 3 8B)
    class MockDescriptor:
        estimated_vram_mb = 4800
    mock_get_model.return_value = MockDescriptor()

    with pytest.raises(ResourceExhaustedError, match="Insufficient VRAM"):
        await manager.admit("llama3.1:8b", "http://mock")

@patch.object(GPUResourceManager, "get_hardware_telemetry")
async def test_concurrency_limit_enforcement(mock_telemetry):
    """
    Validates that unbounded parallel inference is capped at 2 concurrent tasks.
    """
    manager = GPUResourceManager()
    manager._init_state()
    
    # Mock CPU-only or sufficient VRAM fallback
    mock_telemetry.return_value = {"gpu_available": False, "free_vram_mb": 0, "total_vram_mb": 0}
    
    # First two should succeed
    await manager.admit("dummy", "http://mock")
    await manager.admit("dummy", "http://mock")
    
    # Third should fail immediately due to max_concurrency=2
    with pytest.raises(ResourceExhaustedError, match="concurrency limit reached"):
        await manager.admit("dummy", "http://mock")
        
    # Release one, next should succeed
    await manager.release()
    await manager.admit("dummy", "http://mock")
    assert manager.active_inference_count == 2