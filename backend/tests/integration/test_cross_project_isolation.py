# backend/tests/integration/test_cross_project_isolation.py
import pytest
from uuid import uuid4
import jwt
import os
from fastapi import HTTPException
from app.security.auth import verify_project_access

SECRET_KEY = os.getenv("JWT_SECRET", "super-secret-key-change-in-prod")
ALGORITHM = "HS256"

pytestmark = pytest.mark.asyncio

class MockResult:
    def __init__(self, val):
        self.val = val
    def scalar_one_or_none(self):
        return self.val

class MockDB:
    def __init__(self, member_exists=False):
        self.member_exists = member_exists
    async def execute(self, stmt):
        return MockResult("member" if self.member_exists else None)

async def test_cross_project_rejection():
    """Validates that accessing a project the user doesn't belong to raises 403 Forbidden."""
    user = {"id": str(uuid4()), "username": "attacker"}
    project_b_id = uuid4()
    
    # Mock DB where user is NOT in ProjectMember for project_b
    db = MockDB(member_exists=False)
    
    with pytest.raises(HTTPException) as exc:
        await verify_project_access(project_b_id, user, db)
        
    assert exc.value.status_code == 403
    assert "Forbidden" in exc.value.detail

async def test_project_approval():
    """Validates that users successfully access their own projects."""
    user = {"id": str(uuid4()), "username": "legit_user"}
    project_a_id = uuid4()
    
    # Mock DB where user IS in ProjectMember for project_a
    db = MockDB(member_exists=True)
    
    result = await verify_project_access(project_a_id, user, db)
    assert result["username"] == "legit_user"