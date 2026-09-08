from abc import ABC, abstractmethod
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field
from app.monitoring.contracts import ObservationState

DestinationCategory = Literal[
    "local_process",
    "loopback",
    "internal_infrastructure",
    "local_ai_inference",
    "local_knowledge_service",
    "sandbox",
    "external_api",
    "external_cloud_ai",
    "blocked_external",
    "unknown_external",
]
SecurityDecision = Literal["allowed", "blocked", "unknown"]
Direction = Literal["inbound", "outbound"]


class TrustedNetworkPolicy(BaseModel):
    """Configuration used to classify destinations without assuming RFC 1918 is safe."""

    trusted_hosts: list[str] = Field(default_factory=list)
    trusted_subnets: list[str] = Field(default_factory=list)
    local_ai_services: list[str] = Field(default_factory=list)
    knowledge_services: list[str] = Field(default_factory=list)
    sandbox_services: list[str] = Field(default_factory=list)
    cloud_ai_services: list[str] = Field(default_factory=list)
    external_api_hosts: list[str] = Field(default_factory=list)
    default_external_decision: SecurityDecision = "blocked"


class NetworkAuditEvent(BaseModel):
    """Metadata-only record of an observed connection or application request."""

    timestamp: datetime
    source_component: str
    source_process: Optional[str] = None
    destination_category: DestinationCategory
    destination_address: Optional[str] = None
    destination_service: Optional[str] = None
    protocol: str
    direction: Direction
    bytes_transferred: Optional[int] = Field(default=None, ge=0)
    request_classification: str
    decision: SecurityDecision
    task_id: Optional[UUID] = None
    execution_id: Optional[UUID] = None


class SovereigntyMetrics(BaseModel):
    """Truthful aggregate contract for local, external, and blocked activity."""

    local_request_count: Optional[int] = Field(default=None, ge=0)
    local_ai_request_count: Optional[int] = Field(default=None, ge=0)
    internal_request_count: Optional[int] = Field(default=None, ge=0)
    external_api_request_count: Optional[int] = Field(default=None, ge=0)
    cloud_ai_request_count: Optional[int] = Field(default=None, ge=0)
    blocked_external_request_count: Optional[int] = Field(default=None, ge=0)
    external_bytes: Optional[int] = Field(default=None, ge=0)
    local_bytes: Optional[int] = Field(default=None, ge=0)
    monitoring_capability: str
    security_policy_state: str
    category_status: dict[str, ObservationState] = Field(default_factory=dict)
    observation_scope: str
    recent_events: list[NetworkAuditEvent] = Field(default_factory=list)
    last_external_connection: Optional[NetworkAuditEvent] = None
    last_cloud_ai_request: Optional[NetworkAuditEvent] = None


class SovereigntyAuditor(ABC):
    """Collect and classify network activity associated with the workbench."""

    @abstractmethod
    async def observe(self) -> list[NetworkAuditEvent]:
        """Return metadata-only observations available from this adapter."""
        raise NotImplementedError

    @abstractmethod
    def classify(self, destination: str, policy: TrustedNetworkPolicy) -> DestinationCategory:
        """Classify a destination using the configured trusted-network policy."""
        raise NotImplementedError

    @abstractmethod
    def capability(self) -> str:
        """Report the actual monitoring capability, never a stronger implied level."""
        raise NotImplementedError

    @abstractmethod
    async def metrics(self) -> SovereigntyMetrics:
        """Return sourced aggregates with unavailable categories left explicit."""
        raise NotImplementedError
