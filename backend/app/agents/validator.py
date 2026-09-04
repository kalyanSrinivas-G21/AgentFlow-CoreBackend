# backend/app/agents/validator.py (MODIFIED)
import logging
import json
from sqlalchemy import select
from app.agents.schemas import ValidationResult
from app.tasks.models import PlanStep, ToolExecution

logger = logging.getLogger(__name__)

class Validator:
    def __init__(self, db_session=None):
        self.db = db_session

    async def validate(self, agent_run, task) -> ValidationResult:
        logger.info(f"Validating agent run {agent_run.id} for task {task.id}")
        
        if not self.db:
            return ValidationResult(passed=True, reason="Agent workflow completed successfully (no DB).")

        if task.task_type == "code_generation":
            stmt = select(ToolExecution).join(PlanStep).where(
                PlanStep.agent_run_id == agent_run.id,
                PlanStep.tool_name == "test.run",
                ToolExecution.status == "COMPLETED"
            ).order_by(ToolExecution.created_at.desc())
            
            try:
                result = await self.db.execute(stmt)
                latest_test = result.scalars().first()
                
                if latest_test:
                    test_res = json.loads(latest_test.result)
                    if test_res.get("exit_code") != 0:
                        reason = f"test.run failed. stdout: {test_res.get('stdout', '')}, stderr: {test_res.get('stderr', '')}"
                        return ValidationResult(passed=False, reason=reason)
            except Exception as e:
                logger.error(f"Validator execution error: {e}")
                return ValidationResult(passed=False, reason=f"Internal validation error: {e}")

        # Fallback for general tasks or missing constraints
        return ValidationResult(passed=True, reason="Agent workflow completed successfully.")