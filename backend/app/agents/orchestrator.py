# backend/app/agents/orchestrator.py
import logging
import asyncio
from typing import Dict, Any
from app.tasks.models import Task
from app.agents.graph import WorkflowGraph, AgentState
from app.sandbox.runner import run_in_sandbox

logger = logging.getLogger(__name__)

class ToolExecutor:
    """Safely bridges LangGraph step requests to the secure Sandbox."""
    async def execute_step(self, step, task_id: str) -> Any:
        class ToolResult:
            def __init__(self, success, output, error):
                self.success = success
                self.output = output
                self.error = error
                
        if step.tool_name == "sandbox":
            try:
                # The sandbox requires a dictionary of filenames to string content
                files = step.tool_args.get("files", {"main.py": step.tool_args.get("code", "")})
                command = step.tool_args.get("command", ["python", "main.py"])
                
                result = await run_in_sandbox(files=files, command=command)
                
                if result.exit_code == 0:
                    return ToolResult(True, result.stdout, None)
                else:
                    return ToolResult(False, None, f"Exit {result.exit_code}: {result.stderr}")
            except Exception as e:
                logger.error(f"Sandbox Tool Exception: {e}")
                return ToolResult(False, None, str(e))
                
        return ToolResult(False, None, f"Unknown tool: {step.tool_name}")

class AgentOrchestrator:
    """Manages the lifecycle of a LangGraph agent run."""
    def __init__(self, db_session, redis_client):
        self.db = db_session
        self.redis = redis_client
        self.executor = ToolExecutor()

    async def run(self, task: Task) -> Dict[str, Any]:
        """
        Executes the agentic workflow and returns the final payload.
        """
        try:
            workflow = WorkflowGraph(self.db, self.redis, self.executor)
            graph_app = workflow.build()
            
            # Handle string inputs gracefully
            if isinstance(task.input_payload, dict):
                objective = task.input_payload.get("prompt", "") or task.input_payload.get("objective", "")
            else:
                objective = str(task.input_payload)

            initial_state: AgentState = {
                "objective": objective,
                "project_id": str(task.project_id),
                "task_id": str(task.id),
                "context": [],
                "plan": [],
                "current_step_index": 0,
                "step_results": [],
                "step_count": 0,
                "max_steps": 10,
                "final_answer": ""
            }

            logger.info(f"Starting AgentOrchestrator for task {task.id}")
            
            # Call ainvoke on the compiled graph, not the wrapper class
            final_state = await graph_app.ainvoke(initial_state)
            
            return {
                "status": "success",
                "final_answer": final_state.get("final_answer", ""),
                "steps_taken": final_state.get("step_count", 0),
                "tool_results": final_state.get("step_results", [])
            }
            
        except Exception as e:
            logger.exception(f"Agent Orchestrator failed catastrophically: {e}")
            return {"status": "error", "error_detail": str(e)}