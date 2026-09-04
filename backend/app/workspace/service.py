# backend/app/workspace/service.py
import os
from pathlib import Path
from uuid import UUID

class SecurityError(Exception):
    """Raised when a path traversal or boundary violation is detected."""
    pass

# Ensure local safe fallback if not set in config
WORKSPACE_ROOT = Path(os.getenv("WORKSPACE_ROOT", "./workspace_data")).resolve()

class WorkspaceService:
    @staticmethod
    def get_project_dir(project_id: UUID | str) -> Path:
        project_dir = WORKSPACE_ROOT / str(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir.resolve()

    @staticmethod
    def resolve_path(project_id: UUID | str, relative_path: str) -> Path:
        project_dir = WorkspaceService.get_project_dir(project_id)
        
        # Explicitly reject absolute path injection attempts
        path_str = str(relative_path)
        if path_str.startswith("/") or path_str.startswith("\\"):
            raise SecurityError(f"Path traversal detected. Absolute paths are not allowed: '{relative_path}'")
            
        # Resolve evaluating symlinks and '..' traverses
        target_path = (project_dir / relative_path).resolve()
        
        # Strict containment check
        if not target_path.is_relative_to(project_dir):
            raise SecurityError(f"Path traversal detected. Access to '{relative_path}' is denied.")
            
        return target_path