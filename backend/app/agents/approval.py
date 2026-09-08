from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ApprovalRequest(BaseModel):
    approval_id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    execution_id: UUID
    operation: str
    risk_level: str
    status: str = "pending"
    decision_reason: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    decided_at: Optional[datetime] = None


class ApprovalGate(ABC):
    @abstractmethod
    async def request(self, task_id: UUID, execution_id: UUID, operation: str, risk_level: str) -> ApprovalRequest:
        raise NotImplementedError

    @abstractmethod
    async def get(self, approval_id: UUID) -> Optional[ApprovalRequest]:
        raise NotImplementedError

    @abstractmethod
    async def decide(self, approval_id: UUID, approved: bool, reason: str) -> ApprovalRequest:
        raise NotImplementedError


class InMemoryApprovalGate(ApprovalGate):
    def __init__(self):
        self.requests: dict[UUID, ApprovalRequest] = {}

    async def request(self, task_id: UUID, execution_id: UUID, operation: str, risk_level: str) -> ApprovalRequest:
        request = ApprovalRequest(
            task_id=task_id,
            execution_id=execution_id,
            operation=operation,
            risk_level=risk_level,
        )
        self.requests[request.approval_id] = request
        return request

    async def get(self, approval_id: UUID) -> Optional[ApprovalRequest]:
        return self.requests.get(approval_id)

    async def decide(self, approval_id: UUID, approved: bool, reason: str) -> ApprovalRequest:
        request = self.requests[approval_id]
        updated = request.model_copy(update={
            "status": "approved" if approved else "rejected",
            "decision_reason": reason,
            "decided_at": datetime.now(timezone.utc),
        })
        self.requests[approval_id] = updated
        return updated
