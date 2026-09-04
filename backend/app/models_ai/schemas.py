# backend/app/models_ai/schemas.py
from pydantic import BaseModel
from typing import Optional, Dict, Any

class ChatRequest(BaseModel):
    prompt: str
    system: Optional[str] = None
    tier: int = 0
    options: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    model: str
    response: str