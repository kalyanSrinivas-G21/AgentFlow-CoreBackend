# backend/app/agents/validator.py
from pydantic import BaseModel

class ValidationResult(BaseModel):
    passed: bool
    reason: str

class Validator:
    async def validate(self, task, agent_run) -> ValidationResult:
        """
        Validates the outcome of an agent run against the original task objective.
        Will be replaced by LangGraph evaluation nodes in Phase 4.
        """
        return ValidationResult(passed=True, reason="ok")