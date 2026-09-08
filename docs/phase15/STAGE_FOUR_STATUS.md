# Stage Four Status Report

**STAGE:** Four — Core Sovereignty Telemetry

**PRE-FLIGHT 1 (envelope migration plan):** Resolved. New sovereignty audit events emit only the Phase 15 envelope on the dedicated logical `stream:sovereignty` channel. Existing legacy task/agent/tool/resource streams remain unchanged. The decision and retirement marker are recorded in the `Event Envelope Migration` heading in [INTERFACE_CONTRACTS.md](INTERFACE_CONTRACTS.md) and [backend/app/events/migration.py](../../backend/app/events/migration.py). No dual emission is used, preventing duplicate audit counts.

**PRE-FLIGHT 2 (dependency declarations):** Resolved. `PyJWT` and `python-docx` were already present in `backend/requirements.txt`; the targeted Windows gap was `python-magic-bin==0.4.14`, now declared with a Windows platform marker while `python-magic>=0.4.27` remains for non-Windows. Verified local versions were PyJWT 2.13.0, python-docx 1.2.0, and python-magic-bin 0.4.14. The failed full requirements install due to unavailable Windows `paddlepaddle` remains documented separately.

**PRE-FLIGHT 3 (paddlepaddle/Windows):** Recorded, not fixed. PaddleOCR usage is documented in [PLATFORM_NOTES.md](PLATFORM_NOTES.md); the OCR decision remains a Stage Seven concern and does not block application telemetry.

**ENTRY CRITERIA MET:** Yes. [GAP_ANALYSIS.md](GAP_ANALYSIS.md) and [INTERFACE_CONTRACTS.md](INTERFACE_CONTRACTS.md) were reviewed before implementation. The Stage Three contract baseline was not contradicted.

**WHAT WAS BUILT:**

- `backend/app/security/application_auditor.py`: real application-level adapter with configurable hosts, subnets, local AI/knowledge/sandbox services, cloud AI services, external API hosts, metadata-only audit records, bounded history, observation states, capability reporting, and bounded subscribers.
- `backend/app/security/auditor.py`: process-level auditor accessor.
- `backend/app/security/sovereignty_router.py`: authenticated `/api/v1/sovereignty/metrics` JSON endpoint and bounded SSE `/api/v1/sovereignty/events` transport.
- `backend/app/models_ai/ollama_provider.py`: application-observed request records immediately before generate, structured generation, embedding, and streaming HTTP calls.
- `backend/app/events/contracts.py` and `backend/app/events/migration.py`: explicit Phase 15 stream naming and migration marker.
- `backend/requirements.txt`: targeted Windows magic-package declaration.
- `docs/phase15/PLATFORM_NOTES.md`: PaddleOCR/Windows platform risk record.

**NO-FAKE-SOVEREIGNTY CHECK RESULTS:** All three passed.

- **Fresh zero activity:** the actual metrics endpoint returned `local_request_count: 0`, `external_api_request_count: null`, `cloud_ai_request_count: null`, `category_status.external_api_request_count: "not_observed"`, `category_status.cloud_ai_request_count: "not_observed"`, and `monitoring_capability: "Application Level Monitoring Active"`. Local zero is therefore distinguishable from unobserved external categories.
- **Adapter disabled:** `set_enabled(False)` caused metrics to report `monitoring_capability: "Unavailable"`; the test also confirmed no stale active label remained and new observations fail loudly.
- **Controlled external attempt:** an actual `httpx` request attempt to `http://example.invalid/controlled-test` invoked the application request hook, was classified as `external_api`, recorded with `decision: "blocked"`, counted once in `external_api_request_count` and `blocked_external_request_count`, and produced a Phase 15 envelope. No confidential data was sent.

**TESTS ADDED:**

- `backend/contract_tests/test_stage_four_auditor.py`: fresh observation states, controlled external request failure path, unavailable-adapter failure path from Section Eleven network/telemetry degradation, Phase 15 event emission, and actual metrics API response.
- Existing Stage Three structural tests remain in `backend/contract_tests/test_phase15_contracts.py`.

**TEST RESULT:** Pass — `18 passed, 2 warnings in 2.99s` from `venv\Scripts\python.exe -m pytest -q --confcutdir=backend/contract_tests backend/contract_tests/test_phase15_contracts.py backend/contract_tests/test_stage_four_auditor.py`. Warnings are dependency deprecations from FastAPI/Starlette's TestClient integration; no test failed.

**DEVIATIONS FROM THE MASTER PROMPT:** Host-level, container-level, and Windows ETW/WFP monitoring are not claimed or implemented. Application-level telemetry observes only requests explicitly reported by workbench code, and the API exposes that scope. The existing legacy event publisher/consumer was not migrated globally; only new sovereignty events use the Phase 15 envelope as documented. Redis persistence for the dedicated channel is deferred because this stage's concrete minimum is the always-available application adapter and SSE transport.

**BYPASSED-CONTROLS PROGRESS:** Ollama generate, structured generation, embedding, and streaming call sites now report through the application auditor. Remaining open call sites from Stage Three are `backend/app/security/auth.py` endpoint validation, `backend/app/monitoring/sampler.py` resource snapshots, `backend/app/models_ai/resource_manager.py` raw NVML values, `backend/app/sandbox/runner.py` sandbox network enforcement, and legacy event consumers/publishers. Model catalog/routing, tool execution, artifacts, traces, and test database isolation remain deferred to their ordered stages.

**OPEN QUESTIONS FOR THE HUMAN TEAM:** Confirm the production choice between the in-process SSE channel and a durable Redis/PostgreSQL sovereignty stream for multi-worker deployments; confirm whether host/container telemetry privileges will be granted in the target deployment; finalize the PaddleOCR Windows decision in Stage Seven.

**EXIT CRITERIA MET:** Yes. All three pre-flight items were documented before telemetry implementation; the application auditor, classification, metrics API, live SSE transport, unavailable state, blocked external classification, and focused tests are implemented and verified. No Stage Five-through-Thirteen behavior was added.

## Retroactive Pre-flight Addendum Closed Before Stage Five

- **Blocked vs. failed counting:** Confirmed and regression-tested in `backend/contract_tests/test_stage_four_auditor.py`. A blocked external event has envelope `status: "failed"` but `payload.decision: "blocked"` and `payload.destination_category: "external_api"`; `blocked_external_request_count` is incremented from the decision/category path and no technical-failure count is created. The semantic rule is also recorded under `Event Envelope Migration` in `INTERFACE_CONTRACTS.md`.
- **Capability-state degradation:** Confirmed by `test_disabled_adapter_reports_unavailable_without_stale_active_state` in the same test file. Disabling the adapter changes the actual metrics response to `monitoring_capability: "Unavailable"`, and subsequent observations fail loudly rather than retaining stale active state.
