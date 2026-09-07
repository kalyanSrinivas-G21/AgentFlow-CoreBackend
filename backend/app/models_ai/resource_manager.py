# backend/app/models_ai/resource_manager.py
import logging
import asyncio
from typing import Dict, Any, Optional
import httpx

# NVML is imported lazily to support CPU-only environments safely
try:
    import pynvml
    NVML_AVAILABLE = True
except ImportError:
    NVML_AVAILABLE = False

from app.models_ai.registry import get_model

logger = logging.getLogger(__name__)

class ResourceExhaustedError(Exception):
    """Raised when hardware cannot accommodate the requested inference task."""
    pass

class GPUResourceManager:
    """
    Singleton admission controller enforcing strict hardware boundaries (Phase 9).
    Prevents OOM crashes by rejecting/queueing tasks exceeding available VRAM.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GPUResourceManager, cls).__new__(cls)
            cls._instance._init_state()
        return cls._instance

    def _init_state(self):
        self.max_concurrency = 2
        self.active_inference_count = 0
        self.currently_loaded_model: Optional[str] = None
        self.lock = asyncio.Lock()
        
        if NVML_AVAILABLE:
            try:
                pynvml.nvmlInit()
                self.gpu_count = pynvml.nvmlDeviceGetCount()
            except Exception as e:
                logger.warning(f"NVML initialized but failed: {e}")
                self.gpu_count = 0
        else:
            self.gpu_count = 0

    def get_hardware_telemetry(self) -> Dict[str, Any]:
        """Step 9.1: NVML Telemetry"""
        if self.gpu_count == 0:
            return {"gpu_available": False, "free_vram_mb": 0, "total_vram_mb": 0}
            
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0) # Assuming single GPU target (RTX 4050)
            info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            return {
                "gpu_available": True,
                "free_vram_mb": info.free // (1024 * 1024),
                "used_vram_mb": info.used // (1024 * 1024),
                "total_vram_mb": info.total // (1024 * 1024)
            }
        except Exception as e:
            logger.error(f"NVML Telemetry error: {e}")
            return {"gpu_available": False, "free_vram_mb": 0, "total_vram_mb": 0}

    async def _unload_model(self, model_id: str, base_url: str):
        """Step 9.4: Manage Model Load/Unload Churn explicitly to clear VRAM."""
        logger.info(f"ResourceManager: Proactively unloading {model_id} to free VRAM.")
        # Ollama unloads models by sending an empty keep_alive
        payload = {"model": model_id, "keep_alive": 0}
        try:
            async with httpx.AsyncClient() as client:
                await client.post(f"{base_url}/api/generate", json=payload, timeout=5.0)
        except Exception as e:
            logger.warning(f"Failed to cleanly unload model {model_id}: {e}")

    async def admit(self, model_id: str, base_url: str) -> None:
        """
        Step 9.2: Admission Control.
        Raises ResourceExhaustedError if the model cannot safely fit in VRAM.
        """
        async with self.lock:
            # Step 9.3: Concurrency Policy
            if self.active_inference_count >= self.max_concurrency:
                raise ResourceExhaustedError("Global inference concurrency limit reached. Task queued.")

            telemetry = self.get_hardware_telemetry()
            
            # If CPU only, we bypass strict VRAM blocks but still apply concurrency limits
            if not telemetry["gpu_available"]:
                self.active_inference_count += 1
                return

            model_req = get_model(model_id)
            if not model_req:
                logger.warning(f"Model {model_id} not in registry. Admitting blindly, risking OOM.")
                self.active_inference_count += 1
                return

            # Check if we need to swap models
            if self.currently_loaded_model and self.currently_loaded_model != model_id:
                # If we don't have enough free RAM to hold both, force an unload
                if telemetry["free_vram_mb"] < model_req.estimated_vram_mb:
                    await self._unload_model(self.currently_loaded_model, base_url)
                    # Note: We assume the unload takes effect quickly. In production, we might poll NVML again here.
                    
            # Strict VRAM validation
            telemetry_post_unload = self.get_hardware_telemetry()
            
            # We enforce a safety buffer (e.g., 200MB) to prevent absolute edge OOMs
            if model_req.estimated_vram_mb > (telemetry_post_unload["free_vram_mb"] - 200):
                raise ResourceExhaustedError(
                    f"Insufficient VRAM for {model_id}. Required: {model_req.estimated_vram_mb}MB, "
                    f"Free: {telemetry_post_unload['free_vram_mb']}MB. Task queued."
                )

            self.currently_loaded_model = model_id
            self.active_inference_count += 1

    async def release(self):
        """Called in a finally block after inference finishes."""
        async with self.lock:
            self.active_inference_count = max(0, self.active_inference_count - 1)