from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.artifacts.contracts import ArtifactRecord, ArtifactStore, ArtifactType


class InMemoryArtifactStore(ArtifactStore):
    """Bounded provenance store for isolated execution and contract tests."""

    def __init__(self, max_artifacts: int = 256):
        self.max_artifacts = max_artifacts
        self.records: dict[UUID, ArtifactRecord] = {}
        self.contents: dict[UUID, bytes] = {}

    async def create(self, task_id: UUID, execution_id: UUID, generating_step_id: UUID, artifact_type: ArtifactType, file_name: str, content: bytes) -> ArtifactRecord:
        if len(self.records) >= self.max_artifacts:
            raise RuntimeError("Artifact store capacity exhausted")
        artifact_id = uuid4()
        record = ArtifactRecord(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            file_name=file_name,
            workspace_location=f"artifacts/{task_id}/{file_name}",
            task_id=task_id,
            execution_id=execution_id,
            generating_step_id=generating_step_id,
            created_at=datetime.now(timezone.utc),
            size_bytes=len(content),
        )
        self.records[artifact_id] = record
        self.contents[artifact_id] = content
        return record

    async def get(self, artifact_id: UUID) -> ArtifactRecord:
        return self.records[artifact_id]

    async def list_for_task(self, task_id: UUID) -> list[ArtifactRecord]:
        return [record for record in self.records.values() if record.task_id == task_id]
