from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator

AllowedNodeType = Literal["model", "tool", "retrieve", "artifact", "validate", "approval", "condition"]


class WorkflowNode(BaseModel):
    node_id: str
    node_type: AllowedNodeType
    capability_ref: str
    configuration: dict[str, Any] = Field(default_factory=dict)


class WorkflowEdge(BaseModel):
    source: str
    target: str


class WorkflowDefinition(BaseModel):
    workflow_id: str
    nodes: list[WorkflowNode] = Field(min_length=1, max_length=64)
    edges: list[WorkflowEdge] = Field(default_factory=list, max_length=128)

    @model_validator(mode="after")
    def validate_graph(self):
        node_ids = {node.node_id for node in self.nodes}
        if len(node_ids) != len(self.nodes):
            raise ValueError("Workflow node IDs must be unique")
        for edge in self.edges:
            if edge.source not in node_ids or edge.target not in node_ids:
                raise ValueError("Workflow edge references an unknown node")
        adjacency = {node_id: [] for node_id in node_ids}
        for edge in self.edges:
            adjacency[edge.source].append(edge.target)
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node_id: str):
            if node_id in visiting:
                raise ValueError("Workflow cycles are not supported")
            if node_id in visited:
                return
            visiting.add(node_id)
            for target in adjacency[node_id]:
                visit(target)
            visiting.remove(node_id)
            visited.add(node_id)

        for node_id in node_ids:
            visit(node_id)
        return self


class CompiledWorkflow(BaseModel):
    execution_id: UUID = Field(default_factory=uuid4)
    workflow_id: str
    operations: list[dict[str, Any]]


def compile_workflow(definition: WorkflowDefinition) -> CompiledWorkflow:
    return CompiledWorkflow(
        workflow_id=definition.workflow_id,
        operations=[
            {"node_id": node.node_id, "node_type": node.node_type, "capability_ref": node.capability_ref, "configuration": node.configuration}
            for node in definition.nodes
        ],
    )
