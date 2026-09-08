# backend/app/models_ai/router.py
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.models_ai.registry import list_models
from app.models_ai.ollama_provider import OllamaProvider
from app.models_ai.router_v2 import ModelRouter

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

