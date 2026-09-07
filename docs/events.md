# Realtime Events Architecture

## Overview
The Sovereign AI Workbench utilizes **Server-Sent Events (SSE)** and **WebSockets** to stream updates to the frontend without heavy HTTP polling.

Since WebSockets bypass standard OpenAPI documentation, this file serves as the definitive contract for parsing real-time events.

## Wire Format: `EventEnvelope`
Every event pushed to the frontend adheres to the exact same top-level JSON structure.

```json
{
  "event_id": "uuid",
  "event_type": "string",
  "occurred_at": "ISO-8601 Timestamp",
  "source": "string (e.g. task_service, worker, orchestrator)",
  "task_id": "uuid | null",
  "agent_run_id": "uuid | null",
  "correlation_id": "uuid",
  "causation_id": "uuid | null",
  "payload": { ... dynamic dictionary based on event_type ... },
  "schema_version": 1
}