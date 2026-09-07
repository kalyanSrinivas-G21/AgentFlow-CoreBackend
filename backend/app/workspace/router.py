# backend/app/workspace/router.py
import os
from fastapi import APIRouter, UploadFile, File as FastAPIFile, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import shutil
import magic

from app.workspace.service import WorkspaceService
from app.workspace.models import File
from app.db import get_db
from app.security.audit import log_action_sync
from app.security.auth import get_current_user, verify_project_access

router = APIRouter(prefix="/api/v1/projects", tags=["files"])

ALLOWED_TYPES = [
    "image/png", "image/jpeg", "application/pdf",
    "text/csv", "text/plain",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" 
]

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB

@router.post("/{project_id}/files")
async def upload_file(
    project_id: UUID, 
    file: UploadFile = FastAPIFile(...), 
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(verify_project_access)  # Step 11.3: RBAC applied
):
    # Step 11.6: Upload Security Limits & Sanitization
    file.file.seek(0, 2)
    file_size = file.file.tell()
    await file.seek(0)
    
    if file_size > MAX_UPLOAD_SIZE:
        raise HTTPException(413, "Payload Too Large: File exceeds 10MB limit")
        
    safe_filename = os.path.basename(file.filename)

    header_bytes = await file.read(2048)
    await file.seek(0)
    sniffed_mime = magic.from_buffer(header_bytes, mime=True)
    
    if sniffed_mime not in ALLOWED_TYPES:
        raise HTTPException(400, f"Unsupported file type: {sniffed_mime}")
    
    target_path = WorkspaceService.resolve_path(project_id, safe_filename)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    
    with target_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    new_file = File(
        project_id=project_id,
        filename=safe_filename,
        content_type=sniffed_mime,
        file_path=safe_filename
    )
    db.add(new_file)
    
    log_action_sync(
        db=db, 
        actor=user["username"], 
        action="upload_file", 
        target_type="file", 
        target_id=str(new_file.id), 
        details={"filename": safe_filename, "content_type": sniffed_mime}
    )
    
    await db.commit()
    await db.refresh(new_file)
        
    return {"id": str(new_file.id), "filename": new_file.filename}