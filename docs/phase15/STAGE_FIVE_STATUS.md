# Stage Five Status Report

**STAGE:** Five — Resource-Aware Model Management

**PRE-FLIGHT 1 (blocked vs. failed counting):** Resolved before Stage Five implementation. `backend/contract_tests/test_stage_four_auditor.py` now captures the emitted blocked event and proves envelope `status: "failed"` is not used for blocked counting; `payload.decision: "blocked"` and destination category drive `blocked_external_request_count`. The rule is documented in the `Event Envelope Migration` section of [INTERFACE_CONTRACTS.md](INTERFACE_CONTRACTS.md) and the addendum in [STAGE_FOUR_STATUS.md](STAGE_FOUR_STATUS.md).

**PRE-FLIGHT 2 (capability-state degradation test):** Resolved before Stage Five implementation. `test_disabled_adapter_reports_unavailable_without_stale_active_state` proves metrics change to `Unavailable` after adapter disablement and new observations fail loudly; evidence is recorded in the Stage Four addendum.

**ENTRY CRITERIA MET:** Yes. Stage Four status, its addendum, and Section Two of the master prompt were reviewed before model-management edits.

**WHAT WAS BUILT:**

- `backend/app/models_ai/registry_model.py`: complete persistent catalog ORM fields for provider/runtime/location, capabilities, modalities, context, estimated/measured VRAM, device/CPU fallback, configuration, and health/load state.
- `backend/alembic/versions/b7f5c2e4a1d0_restore_model_catalog.py`: restores the model registry table dropped by the current migration history.
- `backend/app/models_ai/catalog.py`: `SqlAlchemyModelCatalog` persistence implementation and explicit `InMemoryModelCatalog` test double.
- `backend/app/models_ai/router_v2.py`: capability, modality, availability, and health-aware local model selection plus runtime execution boundary.
- `backend/app/models_ai/router.py`: existing import surface now exposes the Stage Five router while preserving the synchronous compatibility selector.
- `backend/app/models_ai/runtime.py`: Ollama provider adapter implementing the frozen `ModelRuntime` interface; inference remains on the Stage Four-audited provider path.
- `backend/app/models_ai/resource_manager.py`: real NVML-backed resource snapshots, explicit unavailable state, bounded condition-variable waiting, safe CPU fallback only when declared, idle eviction callbacks, and active-request reference tracking.

**ROUTER-THROUGH-AUDITOR VERIFICATION:** Pass. `test_router_initiated_ollama_request_is_visible_to_auditor` routes an inference through `ModelRouter` and `OllamaRuntime`; the provider request is recorded by the Stage Four auditor as one local AI request. No cloud fallback exists in this path.

**NO-FAKE-TELEMETRY CHECK (VRAM/resource data):** Pass. `NvmlResourceProvider` returns `state: "unavailable"` with `None` VRAM fields when NVML cannot measure the device; it never substitutes zero or an estimate. The test `test_unavailable_vram_is_not_presented_as_zero` verifies this. Measured snapshots carry `state: "measured"` and source metadata; model estimates remain separate catalog fields.

**TESTS ADDED:**

- `backend/contract_tests/test_stage_five_runtime.py`: unavailable-model routing, simulated GPU-OOM-shaped safe rejection, unavailable VRAM honesty, slow-inference eviction blocking, and router-to-auditor visibility.
- Stage Four regression tests remain active for blocked-versus-failed counting and capability degradation.

**TEST RESULT:** Pass — `23 passed, 2 warnings in 3.19s` from `venv\Scripts\python.exe -m pytest -q --confcutdir=backend/contract_tests backend/contract_tests/test_phase15_contracts.py backend/contract_tests/test_stage_four_auditor.py backend/contract_tests/test_stage_five_runtime.py`. The two warnings are existing FastAPI/Starlette TestClient deprecations. Existing database-bound router tests could not be collected in this Windows session because their global fixture resolves the configured development hostname `db`; that isolation issue remains assigned to Stage Eleven and was not bypassed by changing the fixture.

**DEVIATIONS FROM THE MASTER PROMPT:** The Ollama adapter does not claim an undocumented eager-load/unload protocol; it reports provider lifecycle states while the resource manager controls admission and safe eviction. Host GPU telemetry is NVML-only where available; unsupported environments report unavailable. The persistent catalog migration is prepared but was not applied to a live database in this session because the configured `db` service was unavailable.

**BYPASSED-CONTROLS PROGRESS:** The Ollama provider path was closed in Stage Four and remains audited. The router now selects from catalog metadata and executes through `ModelRuntime`/`OllamaRuntime`, with test evidence of auditor visibility. Remaining open items are legacy direct orchestration/provider call sites in `agents/graph.py` (Stage Six), direct embedding-provider routing (Stage Seven), resource sampler integration (Stage Four/Telemetry follow-up), sandbox network reporting (Stage Eight), legacy event replay migration (Stage Nine), artifacts/traces (Stages Six/Nine), and dedicated test database isolation (Stage Eleven).

**OPEN QUESTIONS FOR THE HUMAN TEAM:** Confirm whether production catalog registration should be migration-seeded or managed through an authenticated catalog API; confirm the target GPU/runtime's supported model-load lifecycle semantics; confirm whether multi-worker deployments require moving the in-process resource condition and auditor event channel to Redis/PostgreSQL coordination.

**EXIT CRITERIA MET:** Yes. Both pre-flight items are evidenced, catalog/router/resource manager/swap admission are implemented with async synchronization, router calls remain visible to the auditor, measured versus unavailable VRAM is explicit, OOM and active-eviction tests pass, and no orchestration/tool/artifact behavior was added.
