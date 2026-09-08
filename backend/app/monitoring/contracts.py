from abc import ABC, abstractmethod
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

ObservationState = Literal[
    "measured",
    "not_observed",
    "unavailable",
    "unknown",
    "blocked",
    "allowed",
]
MonitoringCapability = Literal[
    "host_level",
    "container_level",
    "application_level",
    "limited",
    "unavailable",
]


class TelemetryObservation(BaseModel):
    """One sourced observation; an absent measurement is never encoded as zero."""

    metric_name: str
    value: Optional[float] = None
    unit: str
    observed_at: datetime
    source: str
    state: ObservationState
    confidence: Optional[float] = Field(default=None, ge=0, le=1)
    labels: dict[str, str] = Field(default_factory=dict)


class TelemetrySnapshot(BaseModel):
    """Bounded snapshot returned by a telemetry provider."""

    observations: list[TelemetryObservation] = Field(default_factory=list)
    capability: MonitoringCapability
    collected_at: datetime


class TelemetryProvider(ABC):
    """Contract for one real or explicitly labelled telemetry source."""

    @abstractmethod
    async def collect(self) -> TelemetrySnapshot:
        """Collect a sourced snapshot without inventing unavailable values."""
        raise NotImplementedError

    @abstractmethod
    def capability(self) -> MonitoringCapability:
        """Report the strongest monitoring level this provider actually supplies."""
        raise NotImplementedError


class ResourceTelemetry(TelemetryProvider):
    """Contract for CPU, memory, GPU, runtime, and queue resource samples."""

    @abstractmethod
    async def collect_resource_snapshot(self) -> TelemetrySnapshot:
        """Collect resource observations for the current deployment."""
        raise NotImplementedError
