from abc import ABC, abstractmethod
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

ArtifactType = Literal[
    "text",
    "markdown",
    "code",
    "report",
    "structured_data",
    "spreadsheet",
    "document",
    "presentation",
    "image",
    "chart",
]


class ArtifactReference(BaseModel):
    artifact_id: UUID
    artifact_type: ArtifactType
    file_name: str
    workspace_location: str
    preview_available: bool = False
    download_available: bool = True


class ArtifactRecord(ArtifactReference):
    task_id: UUID
    execution_id: UUID
    generating_step_id: UUID
    created_at: datetime
    size_bytes: Optional[int] = Field(default=None, ge=0)


class ArtifactStore(ABC):
    """Provenance-preserving boundary for deliverables inside a project workspace."""

    @abstractmethod
    async def create(
        self,
        task_id: UUID,
        execution_id: UUID,
        generating_step_id: UUID,
        artifact_type: ArtifactType,
        file_name: str,
        content: bytes,
    ) -> ArtifactRecord:
        raise NotImplementedError

    @abstractmethod
    async def get(self, artifact_id: UUID) -> ArtifactRecord:
        raise NotImplementedError

    @abstractmethod
    async def list_for_task(self, task_id: UUID) -> list[ArtifactRecord]:
        raise NotImplementedError
