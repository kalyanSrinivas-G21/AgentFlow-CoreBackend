# backend/app/tasks/schemas.py
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from typing import Dict, Any, Optional
from datetime import datetime

class TaskCreateRequest(BaseModel):
    task_type: str
    input_payload: Dict[str, Any]

class TaskResponse(BaseModel):
    id: UUID
    project_id: UUID
    task_type: str
    status: str
    input_payload: Dict[str, Any]
    result_payload: Optional[Dict[str, Any]] = None
    retry_of_task_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ProjectResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)