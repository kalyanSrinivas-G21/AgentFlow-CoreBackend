# backend/app/agents/planner.py
import json
import logging
from pydantic import BaseModel
from typing import List, Dict, Any
from app.models_ai.tier_router import TierRouter
try:
    from app.models_ai.provider import OllamaProvider
except ImportError:
    from app.models_ai.ollama_provider import OllamaProvider

logger = logging.getLogger(__name__)

class StepSchema(BaseModel):
    tool: str
    tool_args: Dict[str, Any]

class PlanSchema(BaseModel):
    steps: List[StepSchema]

class Planner:
    async def plan(self, objective: str, feedback: str = None) -> dict:
        logger.info(f"Planning for objective: {objective}")
        model_name = TierRouter.get_model_for_tier(1)
        provider = OllamaProvider(model_name)
        
        system_prompt = "You are a planning agent. Break down the objective into a list of tool steps. Output JSON matching the schema."
        prompt_text = f"Objective: {objective}\nReturn JSON with a 'steps' array. Each step needs 'tool' and 'tool_args'."
        
        if feedback:
            prompt_text += f"\nPrevious attempt failed. Feedback: {feedback}\nPlease adjust your plan."
        
        try:
            response = await provider.generate(
                prompt=prompt_text,
                system=system_prompt,
                format="json"
            )
            
            data = json.loads(response.content)
            PlanSchema(**data)
            return data
        except Exception as e:
            logger.error(f"Planning failed: {e}")
            return {"steps": []}