# backend/app/agents/schemas.py
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class PlanStepDraft(BaseModel):
    tool_name: str
    args: Dict[str, Any]
    reason: str

class PlanDraft(BaseModel):
    steps: List[PlanStepDraft]

class ValidationResult(BaseModel):
    passed: bool
    reason: str