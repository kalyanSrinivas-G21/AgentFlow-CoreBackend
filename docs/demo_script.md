# SIH 2026 Demo Script: Sovereign On-Premise Agentic AI Workbench

**Duration:** 4 minutes
**Prerequisites:** 
- Clean slate (`make down`)
- Laptop disconnected from the internet (WiFi OFF).

## Step 1: Cold Start & One-Click Deploy (0:00 - 0:45)
*Action:* Run `make demo` in terminal.
*Talking Track:* "To prove the portability of this system, we are deploying from a completely cold state with no internet connection. The `make demo` command spins up PostgreSQL, Redis, local Ollama, and our FastAPI backend. The system is entirely air-gapped, ensuring complete data residency for defense and industrial IP."

## Step 2: Live Observability (0:45 - 1:15)
*Action:* Open Frontend Dashboard (Monitoring tab).
*Talking Track:* "Because AI can often feel like a black box, we immediately expose live hardware telemetry. You can see the backend sampling our CPU and memory every 5 seconds. This proves the inference is happening locally on this machine, right now."

## Step 3: Multimodal Document Extraction (1:15 - 2:30)
*Action:* Upload a complex technical PDF diagram. Submit an Extraction Task.
*Talking Track:* "We upload a secure diagram. We assign a task to the AI to extract the specifications. Our system uses a local Vision Language Model and `pgvector`. Watch the Event Feed stream—these are live WebSockets broadcasting the Agent's internal decision loop, proving exactly which tools it selects, in real-time."

## Step 4: Immutable Audit & Security (2:30 - 3:30)
*Action:* Show the PostgreSQL `audit_logs` table.
*Talking Track:* "For strict compliance, every tool execution, file upload, and agent step you just saw was synchronously written to an immutable Audit Log. Furthermore, we mathematically intercept the Python socket library—if an Agent attempts to exfiltrate this PDF to an external IP, the Sandbox immediately terminates the process."

## Conclusion (3:30 - 4:00)
*Talking Track:* "In under 4 minutes, offline, we deployed an enterprise-grade, agentic AI platform that is completely sovereign, auditable, and secure. Thank you."