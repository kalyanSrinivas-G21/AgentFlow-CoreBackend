# backend/tests/e2e/test_real_agent_workflow.py
import pytest
import asyncio
import json
from httpx import AsyncClient, ASGITransport
from app.main import app

pytestmark = pytest.mark.asyncio

async def test_real_agent_tool_execution(auth_context):
    """
    Step 12.5: Real Agent Testing.
    Assigns an abstract goal requiring the LangGraph planner to execute the sandbox tool.
    """
    project_id = auth_context["project_id"]
    headers = {"Authorization": f"Bearer {auth_context['token']}"}
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        req_data = {
            "task_type": "agentic_workflow",
            "input_payload": {"prompt": "Write a python script that prints the word 'BANANA' to stdout, then execute it using the sandbox tool."}
        }
        res = await client.post(f"/api/v1/projects/{project_id}/tasks", json=req_data, headers=headers)
        assert res.status_code == 201, f"Task creation failed: {res.text}"
        task_id = res.json()["id"]
        
        for _ in range(60):
            await asyncio.sleep(2)
            poll = await client.get(f"/api/v1/tasks/{task_id}", headers=headers)
            assert poll.status_code == 200
            data = poll.json()
            
            if data["status"] in ["COMPLETED", "FAILED"]:
                result_payload = data.get("result_payload", {})
                
                # If it's a string (e.g. from DB serialization), parse it back to a dict
                if isinstance(result_payload, str):
                    try:
                        # Sometimes python dicts are stored as strings with single quotes
                        result_payload = eval(result_payload)
                    except:
                        pass
                
                result_str = str(result_payload)
                
                if data["status"] == "FAILED" or result_payload.get("status") == "error":
                    pytest.fail(f"Agent Orchestrator failed: {result_str}")
                
                assert data["status"] == "COMPLETED", f"Agent failed: {data}"
                
                # Check explicitly if BANANA is in the raw stringified dictionary
                assert "BANANA" in result_str.upper(), f"Expected BANANA but got: {result_str}"
                return
        
        pytest.fail("Agent workflow timed out. The agent failed to complete the multi-step plan.")