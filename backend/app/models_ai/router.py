# backend/app/models_ai/router.py
import os
from fastapi import APIRouter, HTTPException
from app.models_ai.schemas import ChatRequest, ChatResponse
from app.models_ai.ollama_provider import OllamaProvider
from app.models_ai.tier_router import TierRouter

router = APIRouter(tags=["ai"])

@router.post("/chat", response_model=ChatResponse)
async def synchronous_chat(req: ChatRequest):
    """
    Synchronous HTTP chat endpoint (Slice 1). 
    Bypasses the async worker queue to test direct LLM connectivity.
    """
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    timeout = float(os.getenv("TIER0_TIMEOUT_S", "120.0"))
    
    provider = OllamaProvider(base_url=base_url, timeout_s=timeout)
    tier_router = TierRouter()
    
    try:
        model_name = tier_router.get_model_for_tier(req.tier)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    try:
        response_text = await provider.generate(
            model=model_name,
            prompt=req.prompt,
            system=req.system,
            options=req.options
        )
        return ChatResponse(model=model_name, response=response_text)
    except Exception as e:
        # Catch httpx timeouts, connection errors, or Ollama server errors
        raise HTTPException(status_code=502, detail=f"LLM Provider Error: {str(e)}")