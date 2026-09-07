# backend/app/models_ai/registry.py
from typing import List, Dict, Optional
from pydantic import BaseModel, Field

class ModelDescriptor(BaseModel):
    model_id: str = Field(..., description="The unique identifier for Ollama (e.g., llama3.1:8b)")
    provider: str = Field(default="ollama")
    capabilities: List[str] = Field(default_factory=list, description="Capabilities like 'vision', 'coding', 'tool_calling'")
    context_length: int = Field(default=8192)
    estimated_vram_mb: int = Field(..., description="Estimated VRAM consumption required to run this model safely")

# Static registry for a 6GB VRAM target architecture (e.g., RTX 4050)
# NVML admission control in Phase 9 will use these static estimates.
_REGISTRY = {
    "llama3.1:8b": ModelDescriptor(
        model_id="llama3.1:8b",
        capabilities=["tool_calling", "general"],
        estimated_vram_mb=4800 # ~4.8 GB quantized
    ),
    "qwen2.5-coder:7b": ModelDescriptor(
        model_id="qwen2.5-coder:7b",
        capabilities=["coding", "general"],
        estimated_vram_mb=4500
    ),
    "llava:7b": ModelDescriptor(
        model_id="llava:7b",
        capabilities=["vision", "general"],
        estimated_vram_mb=4500
    ),
    "nomic-embed-text": ModelDescriptor(
        model_id="nomic-embed-text",
        capabilities=["embedding"],
        estimated_vram_mb=800
    )
}

def get_model(model_id: str) -> Optional[ModelDescriptor]:
    return _REGISTRY.get(model_id)

def list_models() -> List[ModelDescriptor]:
    return list(_REGISTRY.values())