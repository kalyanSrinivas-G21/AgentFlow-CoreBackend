from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.artifacts.store import InMemoryArtifactStore
from app.workflow import WorkflowDefinition, compile_workflow


def test_invalid_workflow_cycle_is_rejected():
    with pytest.raises(ValidationError, match="cycles"):
        WorkflowDefinition(
            workflow_id="cycle",
            nodes=[
                {"node_id": "a", "node_type": "tool", "capability_ref": "safe"},
                {"node_id": "b", "node_type": "validate", "capability_ref": "validator"},
            ],
            edges=[{"source": "a", "target": "b"}, {"source": "b", "target": "a"}],
        )


def test_workflow_compiles_only_registered_capability_shapes():
    definition = WorkflowDefinition(
        workflow_id="valid",
        nodes=[{"node_id": "a", "node_type": "tool", "capability_ref": "safe_tool"}],
    )
    compiled = compile_workflow(definition)
    assert compiled.operations[0]["capability_ref"] == "safe_tool"
    assert "code" not in compiled.operations[0]


@pytest.mark.asyncio
async def test_artifact_keeps_provenance_and_is_bounded():
    store = InMemoryArtifactStore(max_artifacts=1)
    task_id, execution_id, step_id = uuid4(), uuid4(), uuid4()
    record = await store.create(task_id, execution_id, step_id, "report", "report.md", b"report")
    assert record.task_id == task_id
    assert record.execution_id == execution_id
    assert record.generating_step_id == step_id
    with pytest.raises(RuntimeError, match="capacity"):
        await store.create(task_id, execution_id, step_id, "report", "second.md", b"x")
