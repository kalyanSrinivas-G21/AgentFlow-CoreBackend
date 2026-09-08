# backend/tests/unit/test_model_router.py
import pytest
from app.models_ai.router_v2 import ModelRouter

@pytest.mark.asyncio
async def test_model_router_capabilities():
    router = ModelRouter()
    
    # 1. Vision routing
    vision_entry = await router.select(required_capabilities=["vision"])
    assert "llava" in vision_entry.model_id.lower() or "vision" in vision_entry.model_id.lower()
    
    # 2. Coding routing
    coding_entry = await router.select(required_capabilities=["coding"])
    assert "coder" in coding_entry.model_id.lower() or "code" in coding_entry.model_id.lower()
    
    # 3. General routing
    general_entry = await router.select(required_capabilities=["general"])
    assert general_entry.model_id is not None

@pytest.mark.asyncio
async def test_model_router_impossible_constraint():
    router = ModelRouter()
    
    with pytest.raises(ValueError, match="No registered model satisfies capabilities"):
        await router.select(required_capabilities=["telepathy"])