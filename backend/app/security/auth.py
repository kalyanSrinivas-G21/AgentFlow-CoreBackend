# backend/app/security/auth.py
import os
import urllib.parse
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import get_db
from app.security.models import ProjectMember

security = HTTPBearer()

# The fallback is a 40-character local-dev-only secret that meets the 32-byte
# HMAC-SHA256 minimum and eliminates the InsecureKeyLengthWarning.
# In any real deployment set JWT_SECRET to a 64-byte+ random value via env.
SECRET_KEY = os.getenv("JWT_SECRET", "local-dev-only-secret-key-not-for-production-use!")
ALGORITHM = "HS256"

# Step 11.5: Local Endpoint Sovereignty Policy
def validate_local_endpoint(url: str):
    """Enforces that AI connections are strictly local/on-premise."""
    parsed = urllib.parse.urlparse(url)
    hostname = parsed.hostname or ""
    allowed_hosts = {"localhost", "127.0.0.1", "ollama", "host.docker.internal", "0.0.0.0", "::1"}
    
    if hostname not in allowed_hosts and not hostname.endswith(".local"):
        raise ValueError(f"Sovereignty Policy Violation: External endpoint {hostname} is strictly blocked.")

# Step 11.1 & 11.2: Standard JWT Implementation
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Validates the JWT and extracts the user identity."""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token: missing sub")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    return {"id": user_id, "username": payload.get("username", "unknown")}

# Step 11.3: Project-Level RBAC
async def verify_project_access(
    project_id: UUID, 
    user: dict = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Ensures the authenticated user belongs to the requested project."""
    stmt = select(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == UUID(user["id"])
    )
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(status_code=403, detail="Forbidden: You do not have access to this project")
    return user

async def verify_ws_project_access(token: str, project_id: UUID, db: AsyncSession) -> dict:
    """Variant of RBAC explicitly for WebSocket connections."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
    except jwt.PyJWTError:
        raise Exception("Invalid or Expired Token")
        
    stmt = select(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == UUID(user_id)
    )
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        raise Exception("Forbidden: Cross-Project Access Denied")
    return {"id": user_id}