# backend/tests/unit/test_model_router.py
import pytest
from app.models_ai.router import ModelRouter

def test_model_router_capabilities():
    router = ModelRouter()
    
    # 1. Vision routing
    vision_model = router.route(required_capabilities=["vision"])
    assert vision_model == "llava:7b"
    
    # 2. Coding routing
    coding_model = router.route(required_capabilities=["coding"])
    assert coding_model == "qwen2.5-coder:7b"
    
    # 3. Explicit override with fallback behavior
    explicit_success = router.route(explicit_model="llama3.1:8b", required_capabilities=["general"])
    assert explicit_success == "llama3.1:8b"
    
    # 4. Explicit override failing capability check cascades to 'auto'
    cascade = router.route(explicit_model="llama3.1:8b", required_capabilities=["vision"])
    assert cascade == "llava:7b"

def test_model_router_impossible_constraint():
    router = ModelRouter()
    
    with pytest.raises(ValueError, match="No registered model satisfies capabilities"):
        router.route(required_capabilities=["telepathy"])