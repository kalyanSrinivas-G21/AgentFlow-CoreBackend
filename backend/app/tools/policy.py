# backend/app/tools/policy.py
import logging
from uuid import UUID
from pydantic import BaseModel, ValidationError
from app.tools.base import TOOL_REGISTRY
from app.workspace.service import WorkspaceService, SecurityError

logger = logging.getLogger(__name__)

class PolicyDecision(BaseModel):
    allowed: bool
    reason: str | None = None

class PolicyEngine:
    @staticmethod
    def check(tool_name: str, args: dict, project_id: UUID | str) -> PolicyDecision:
        """Evaluates a requested tool call and returns a deterministic allow/deny decision."""
        try:
            if tool_name not in TOOL_REGISTRY:
                return PolicyDecision(allowed=False, reason=f"Unregistered tool: {tool_name}")
            
            tool = TOOL_REGISTRY[tool_name]
            
            try:
                # Validate argument payload structure
                parsed_args = tool.input_schema(**args)
            except ValidationError as e:
                return PolicyDecision(allowed=False, reason=f"Invalid arguments: {e.errors()}")
            
            # Context-specific security evaluations
            if tool_name.startswith("filesystem."):
                path_arg = args.get("path")
                if path_arg:
                    try:
                        # Dry-run the path resolution to trap traversal attacks early
                        WorkspaceService.resolve_path(project_id, path_arg)
                    except SecurityError as e:
                        return PolicyDecision(allowed=False, reason=str(e))
                    except Exception as e:
                        return PolicyDecision(allowed=False, reason=f"Path evaluation error: {e}")
            
            return PolicyDecision(allowed=True)
            
        except Exception as e:
            logger.exception("Unexpected error in PolicyEngine check.")
            # Fail closed
            return PolicyDecision(allowed=False, reason="Internal policy evaluation error (fails closed).")