# backend/tests/unit/test_policy_engine.py
import pytest
import uuid
from app.tools.policy import PolicyEngine

def test_policy_engine_unknown_tool():
    project_id = uuid.uuid4()
    decision = PolicyEngine.check("hacker.nuke", {}, project_id)
    assert decision.allowed is False
    assert "Unregistered tool" in decision.reason

def test_policy_engine_invalid_args():
    project_id = uuid.uuid4()
    # filesystem.write expects 'path' and 'content'
    decision = PolicyEngine.check("filesystem.write", {"path": "only_path"}, project_id)
    assert decision.allowed is False
    assert "Invalid arguments" in decision.reason

def test_policy_engine_path_traversal():
    project_id = uuid.uuid4()
    # Attempt to write outside the workspace
    decision = PolicyEngine.check("filesystem.write", {"path": "../../../etc/passwd", "content": "pwned"}, project_id)
    assert decision.allowed is False
    assert "Path traversal detected" in decision.reason

def test_policy_engine_absolute_path_traversal():
    project_id = uuid.uuid4()
    # Attempt absolute path injection
    decision = PolicyEngine.check("filesystem.write", {"path": "/etc/shadow", "content": "pwned"}, project_id)
    assert decision.allowed is False
    assert "Path traversal detected" in decision.reason

def test_policy_engine_valid():
    project_id = uuid.uuid4()
    decision = PolicyEngine.check("filesystem.write", {"path": "test.txt", "content": "hello"}, project_id)
    assert decision.allowed is True