import pytest

from app.sandbox.runner import run_in_sandbox
from app.tools.base import TOOL_REGISTRY, get_tool_catalog
from app.tools.policy import PolicyEngine


def test_registered_tool_catalog_exposes_execution_contract_metadata():
    catalog = get_tool_catalog()
    assert catalog
    assert all("tool_id" in item for item in catalog)
    assert all("execution_environment" in item for item in catalog)
    assert all("network_policy" in item for item in catalog)


@pytest.mark.asyncio
async def test_sandbox_rejects_workspace_escape_before_docker_start():
    with pytest.raises(ValueError, match="Path traversal"):
        await run_in_sandbox({"../escape.py": "print('blocked')"}, ["python", "escape.py"])


def test_policy_fails_closed_for_unregistered_tool():
    decision = PolicyEngine.check("not-registered", {}, "project")
    assert decision.allowed is False
    assert "Unregistered" in (decision.reason or "")
