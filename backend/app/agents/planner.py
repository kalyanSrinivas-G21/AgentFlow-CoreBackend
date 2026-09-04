# backend/app/agents/planner.py
import os
import json
import logging
from typing import List, Optional
from app.agents.schemas import PlanDraft, PlanStepDraft
from app.models_ai.tier_router import TierRouter
from app.models_ai.ollama_provider import OllamaProvider

logger = logging.getLogger(__name__)

class Planner:
    def __init__(self):
        self.tier_router = TierRouter()
        self.model = self.tier_router.get_model_for_tier(1)
        self.provider = OllamaProvider(base_url=os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"))

    async def plan(self, prompt: str, prior_failure: Optional[str] = None) -> List[PlanStepDraft]:
        system_prompt = (
            "You are an expert AI planner. Break down the user's objective into a logical sequence of tool executions. "
            "Output valid JSON conforming exactly to the requested schema."
        )
        
        user_prompt = f"Objective: {prompt}"
        if prior_failure:
            user_prompt += f"\n\nWARNING: Your previous plan failed validation. Reason: {prior_failure}. " \
                           f"Adjust your steps to resolve this failure."

        schema = PlanDraft.model_json_schema()
        
        try:
            logger.info(f"Planner requesting plan from {self.model}...")
            response = await self.provider.generate_structured(
                model=self.model,
                prompt=user_prompt,
                schema=schema,
                system=system_prompt
            )
            
            if "error" in response:
                raise ValueError(f"Planner LLM generation error: {response['error']}")
                
            steps = response.get("steps", [])
            return [PlanStepDraft(**step) for step in steps]
            
        except Exception as e:
            logger.exception("Failed to generate plan.")
            raise