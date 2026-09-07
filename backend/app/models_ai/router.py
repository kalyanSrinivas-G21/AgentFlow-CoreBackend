# backend/app/models_ai/router.py
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.models_ai.registry import get_model, list_models
from app.models_ai.ollama_provider import OllamaProvider

logger = logging.getLogger(__name__)

router = APIRouter(tags=["AI Models"])

class ModelResponse(BaseModel):
    models: List[Dict[str, Any]]

@router.get("/models", response_model=ModelResponse)
async def get_models_api():
    """Step 13.1: Returns the capability-aware model registry to the frontend/client."""
    return {"models": [model.model_dump() for model in list_models()]}

class ChatStreamRequest(BaseModel):
    model: str = "auto"
    prompt: str
    system: Optional[str] = None

@router.post("/chat/stream")
async def chat_stream(req: ChatStreamRequest):
    """Server-Sent Events (SSE) stream for real-time LLM token generation."""
    router_svc = ModelRouter()
    model_name = router_svc.route(explicit_model=req.model, required_capabilities=["general"])
    provider = OllamaProvider()

    async def event_generator():
        try:
            async for chunk in provider.stream(model=model_name, prompt=req.prompt, system=req.system):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"Streaming failed: {e}")
            yield f"data: [ERROR] {str(e)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

class ModelRouter:
    """Capability-aware router with fallback support."""
    def __init__(self):
        self.priority_chains = {
            "coding": ["qwen2.5-coder:7b", "llama3.1:8b"],
            "vision": ["llava:7b"],
            "tool_calling": ["llama3.1:8b", "qwen2.5-coder:7b"],
            "general": ["llama3.1:8b", "qwen2.5-coder:7b"],
            "embedding": ["nomic-embed-text"]
        }

    def route(self, explicit_model: Optional[str] = None, required_capabilities: List[str] = None) -> str:
        if required_capabilities is None:
            required_capabilities = ["general"]

        if explicit_model and explicit_model != "auto":
            model = get_model(explicit_model)
            if not model:
                logger.warning(f"Explicit model {explicit_model} not found in registry. Falling back to auto.")
            else:
                missing_caps = [c for c in required_capabilities if c not in model.capabilities]
                if missing_caps:
                    logger.warning(f"Explicit model {explicit_model} lacks required capabilities. Falling back to auto.")
                else:
                    return model.model_id

        primary_cap = required_capabilities[0] 
        chain = self.priority_chains.get(primary_cap, self.priority_chains["general"])

        for candidate_id in chain:
            model = get_model(candidate_id)
            if not model: continue
            if all(cap in model.capabilities for cap in required_capabilities):
                return model.model_id

        raise ValueError(f"No registered model satisfies capabilities: {required_capabilities}")

    def get_embedding_model(self) -> str:
        return self.route(required_capabilities=["embedding"])