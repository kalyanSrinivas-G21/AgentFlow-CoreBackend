# backend/app/security/auth.py
import os
import secrets
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()
DEMO_ADMIN_TOKEN = os.getenv("DEMO_ADMIN_TOKEN", "supersecret-demo-token")

async def get_current_actor(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Validates the Bearer token using constant-time comparison to prevent timing attacks.
    Returns the actor name ('demo_admin') on success, raises 401 on failure.
    """
    is_valid = secrets.compare_digest(credentials.credentials, DEMO_ADMIN_TOKEN)
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    return "demo_admin"