# backend/app/models_ai/tier_router.py
import os

class TierRouter:
    """
    Deterministically routes tasks to specific models based on the required tier.
    Tier 0: Small, fast, capable of basic routing/formatting (e.g., Llama 3 8B, Qwen 2.5 7B)
    Tier 1: Medium, strong reasoning (e.g., Mixtral 8x7B, Command R)
    Tier 2: Large, complex planning/coding (e.g., Llama 3 70B, WizardLM 8x22B)
    """
    
    def __init__(self):
        self.tier0 = os.getenv("MODEL_TIER0", "llama3.1")
        self.tier1 = os.getenv("MODEL_TIER1", "mixtral")
        self.tier2 = os.getenv("MODEL_TIER2", "llama3.1:70b")
        self.embedding = os.getenv("MODEL_EMBEDDING", "nomic-embed-text")

    def get_model_for_tier(self, tier: int) -> str:
        if tier == 0:
            return self.tier0
        elif tier == 1:
            return self.tier1
        elif tier == 2:
            return self.tier2
        else:
            raise ValueError(f"Unknown tier: {tier}")
            
    def get_embedding_model(self) -> str:
        return self.embedding