import asyncio
import ipaddress
import os
from collections import Counter, deque
from datetime import datetime, timezone
from typing import AsyncIterator, Optional
from urllib.parse import urlparse
from uuid import UUID

from app.events.contracts import EventEnvelope
from app.security.sovereignty import (
    DestinationCategory,
    Direction,
    NetworkAuditEvent,
    SecurityDecision,
    SovereigntyAuditor,
    SovereigntyMetrics,
    TrustedNetworkPolicy,
)


class ApplicationTelemetryAuditor(SovereigntyAuditor):
    """Always-available application-level network auditor.

    This adapter observes requests explicitly reported by workbench components. It
    does not claim to see unrelated host or container traffic.
    """

    def __init__(
        self,
        policy: Optional[TrustedNetworkPolicy] = None,
        history_limit: int = 256,
        subscriber_queue_size: int = 64,
    ) -> None:
        self.policy = policy or self.policy_from_environment()
        self.history: deque[NetworkAuditEvent] = deque(maxlen=history_limit)
        self._counts: Counter[str] = Counter()
        self._bytes: Counter[str] = Counter()
        self._subscribers: set[asyncio.Queue[EventEnvelope]] = set()
        self._sequence = 0
        self._subscriber_queue_size = subscriber_queue_size
        self._enabled = True
        self._last_external: Optional[NetworkAuditEvent] = None
        self._last_cloud_ai: Optional[NetworkAuditEvent] = None
        self._lock = asyncio.Lock()

    @staticmethod
    def _csv(name: str) -> list[str]:
        return [item.strip() for item in os.getenv(name, "").split(",") if item.strip()]

    @classmethod
    def policy_from_environment(cls) -> TrustedNetworkPolicy:
        """Build policy from deployment configuration, with no guessed private subnets."""
        configured_ai_services = cls._csv("SOVEREIGN_LOCAL_AI_SERVICES")
        if not configured_ai_services:
            configured_ai_services = [cls._host(os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))]
        return TrustedNetworkPolicy(
            trusted_hosts=cls._csv("SOVEREIGN_TRUSTED_HOSTS"),
            trusted_subnets=cls._csv("SOVEREIGN_TRUSTED_SUBNETS"),
            local_ai_services=configured_ai_services,
            knowledge_services=cls._csv("SOVEREIGN_KNOWLEDGE_SERVICES"),
            sandbox_services=cls._csv("SOVEREIGN_SANDBOX_SERVICES"),
            cloud_ai_services=cls._csv("SOVEREIGN_CLOUD_AI_SERVICES"),
            external_api_hosts=cls._csv("SOVEREIGN_EXTERNAL_API_HOSTS"),
            default_external_decision=os.getenv("SOVEREIGN_DEFAULT_EXTERNAL_DECISION", "blocked"),
        )

    @staticmethod
    def _host(destination: str) -> str:
        parsed = urlparse(destination if "://" in destination else f"//{destination}")
        return (parsed.hostname or destination).strip("[]").lower()

    @staticmethod
    def _matches(host: str, configured: list[str]) -> bool:
        return host in {item.lower() for item in configured}

    @staticmethod
    def _in_subnet(host: str, configured: list[str]) -> bool:
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            return False
        for subnet in configured:
            try:
                if address in ipaddress.ip_network(subnet, strict=False):
                    return True
            except ValueError:
                continue
        return False

    def classify(self, destination: str, policy: TrustedNetworkPolicy) -> DestinationCategory:
        host = self._host(destination)
        if self._matches(host, policy.local_ai_services):
            return "local_ai_inference"
        if self._matches(host, policy.knowledge_services):
            return "local_knowledge_service"
        if self._matches(host, policy.sandbox_services):
            return "sandbox"
        if self._matches(host, policy.cloud_ai_services):
            return "external_cloud_ai"
        if self._matches(host, policy.external_api_hosts):
            return "external_api"
        try:
            if ipaddress.ip_address(host).is_loopback or host == "localhost":
                return "loopback"
        except ValueError:
            pass
        if self._matches(host, policy.trusted_hosts) or self._in_subnet(host, policy.trusted_subnets):
            return "internal_infrastructure"
        if policy.default_external_decision == "blocked":
            return "blocked_external"
        return "unknown_external"

    @staticmethod
    def _decision(category: DestinationCategory, policy: TrustedNetworkPolicy) -> SecurityDecision:
        if category in {"local_process", "loopback", "internal_infrastructure", "local_ai_inference", "local_knowledge_service", "sandbox"}:
            return "allowed"
        if category in {"external_api", "external_cloud_ai"}:
            return policy.default_external_decision
        return "blocked" if policy.default_external_decision == "blocked" else "unknown"

    def capability(self) -> str:
        return "Application Level Monitoring Active" if self._enabled else "Unavailable"

    async def observe(self) -> list[NetworkAuditEvent]:
        async with self._lock:
            return list(self.history)

    async def record_request(
        self,
        destination: str,
        source_component: str,
        protocol: str = "http",
        direction: Direction = "outbound",
        bytes_transferred: Optional[int] = None,
        request_classification: str = "application_request",
        decision: Optional[SecurityDecision] = None,
        task_id: Optional[UUID] = None,
        execution_id: Optional[UUID] = None,
    ) -> NetworkAuditEvent:
        """Record one application-observed request and publish its Phase 15 envelope."""
        category = self.classify(destination, self.policy)
        selected_decision = decision or self._decision(category, self.policy)
        if not self._enabled:
            selected_decision = "unknown"

        event = NetworkAuditEvent(
            timestamp=datetime.now(timezone.utc),
            source_component=source_component,
            destination_category=category,
            destination_address=self._host(destination),
            destination_service=destination,
            protocol=protocol,
            direction=direction,
            bytes_transferred=bytes_transferred,
            request_classification=request_classification,
            decision=selected_decision,
            task_id=task_id,
            execution_id=execution_id,
        )
        async with self._lock:
            if not self._enabled:
                raise RuntimeError("Application telemetry auditor is unavailable")
            self.history.append(event)
            self._counts[category] += 1
            if selected_decision == "blocked" and category != "blocked_external":
                self._counts["blocked_external"] += 1
            if bytes_transferred is not None:
                scope = "local" if category in {"loopback", "local_process", "local_ai_inference", "local_knowledge_service", "sandbox", "internal_infrastructure"} else "external"
                self._bytes[scope] += bytes_transferred
            if category in {"external_api", "external_cloud_ai", "blocked_external", "unknown_external"}:
                self._last_external = event
            if category == "external_cloud_ai":
                self._last_cloud_ai = event
            envelope = self._to_envelope(event)
            subscribers = tuple(self._subscribers)

        for subscriber in subscribers:
            try:
                subscriber.put_nowait(envelope)
            except asyncio.QueueFull:
                try:
                    subscriber.get_nowait()
                    subscriber.put_nowait(envelope)
                except asyncio.QueueEmpty:
                    pass
        return event

    def _to_envelope(self, event: NetworkAuditEvent) -> EventEnvelope:
        self._sequence += 1
        return EventEnvelope(
            event_type="sovereignty.network.observed",
            project_id=None,
            task_id=event.task_id,
            execution_id=event.execution_id,
            component=event.source_component,
            status="succeeded" if event.decision == "allowed" else "failed",
            payload=event.model_dump(mode="json"),
            sequence_number=self._sequence,
        )

    async def metrics(self) -> SovereigntyMetrics:
        async with self._lock:
            observed_external = self._counts["external_api"] + self._counts["external_cloud_ai"]
            external_status = "measured" if observed_external else "not_observed"
            return SovereigntyMetrics(
                local_request_count=sum(self._counts[category] for category in ("loopback", "local_process", "internal_infrastructure", "local_ai_inference", "local_knowledge_service", "sandbox")),
                local_ai_request_count=self._counts["local_ai_inference"],
                internal_request_count=self._counts["internal_infrastructure"],
                external_api_request_count=self._counts["external_api"] if self._counts["external_api"] else None,
                cloud_ai_request_count=self._counts["external_cloud_ai"] if self._counts["external_cloud_ai"] else None,
                blocked_external_request_count=self._counts["blocked_external"],
                external_bytes=self._bytes["external"] if self._bytes["external"] else None,
                local_bytes=self._bytes["local"] if self._bytes["local"] else 0,
                monitoring_capability=self.capability(),
                security_policy_state=self.policy.default_external_decision,
                category_status={
                    "local_request_count": "measured",
                    "local_ai_request_count": "measured",
                    "internal_request_count": "measured",
                    "external_api_request_count": external_status,
                    "cloud_ai_request_count": "measured" if self._counts["external_cloud_ai"] else "not_observed",
                    "blocked_external_request_count": "measured",
                    "external_bytes": external_status,
                    "local_bytes": "measured",
                },
                observation_scope="application_requests_reported_to_auditor_only",
                recent_events=list(self.history),
                last_external_connection=self._last_external,
                last_cloud_ai_request=self._last_cloud_ai,
            )

    async def subscribe(self) -> asyncio.Queue[EventEnvelope]:
        queue: asyncio.Queue[EventEnvelope] = asyncio.Queue(maxsize=self._subscriber_queue_size)
        async with self._lock:
            self._subscribers.add(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue[EventEnvelope]) -> None:
        async with self._lock:
            self._subscribers.discard(queue)

    async def set_enabled(self, enabled: bool) -> None:
        async with self._lock:
            self._enabled = enabled
