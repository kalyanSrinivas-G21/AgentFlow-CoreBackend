# backend/app/workspace/router.py
from fastapi import APIRouter, UploadFile, File as FastAPIFile, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import shutil

from app.workspace.service import WorkspaceService
from app.workspace.models import File
from app.db import get_db
from app.security.audit import log_action_sync
from app.security.auth import get_current_actor

router = APIRouter(prefix="/api/v1/projects", tags=["files"])

ALLOWED_TYPES = ["image/png", "image/jpeg", "application/pdf"]

@router.post("/{project_id}/files")
async def upload_file(
    project_id: UUID, 
    file: UploadFile = FastAPIFile(...), 
    db: AsyncSession = Depends(get_db),
    actor: str = Depends(get_current_actor)
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, "Unsupported file type. Use PNG, JPEG, or PDF.")
    
    # Securely resolve path and save
    target_path = WorkspaceService.resolve_path(project_id, file.filename)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    
    with target_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    new_file = File(
        project_id=project_id,
        filename=file.filename,
        content_type=file.content_type,
        file_path=file.filename
    )
    
    db.add(new_file)
    
    # Atomic Audit Log Registration
    log_action_sync(
        db=db, 
        actor=actor, 
        action="upload_file", 
        target_type="file", 
        target_id=str(new_file.id), 
        details={"filename": file.filename, "content_type": file.content_type}
    )
    
    await db.commit()
    await db.refresh(new_file)
        
    return {"id": str(new_file.id), "filename": new_file.filename}