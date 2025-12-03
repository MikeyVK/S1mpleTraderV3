# SimpleTraderV3 - Implementation TODO

**Status:** LIVING DOCUMENT  
**Last Updated:** 2025-12-02  
**Update Frequency:** Daily (during active development)

---

## Current Focus

Week 1: Configuration Schemas (CRITICAL PATH - blocker for all subsequent work)

> **Quick Status:** 456 tests passing, Week 0 complete, Week 1 in progress

---

## Quick Links

| Document | Purpose |
|----------|---------|
| [IMPLEMENTATION_STATUS.md](implementation/IMPLEMENTATION_STATUS.md) | Quality metrics & test counts |
| [TODO_DOCUMENTATION.md](TODO_DOCUMENTATION.md) | Missing docs & broken links |
| [DOCUMENTATION_MAINTENANCE.md](DOCUMENTATION_MAINTENANCE.md) | Doc organization rules |

**Navigation:**
- **📖 Agent Instructions:** [../agent.md](../agent.md) - AI assistant guide
- **🏛️ Architecture:** [architecture/README.md](architecture/README.md) - System design
- **✨ Coding Standards:** [coding_standards/README.md](coding_standards/README.md) - TDD, quality gates
- **📋 Reference:** [reference/README.md](reference/README.md) - Templates

**Archived:** [development/#Archief/](development/#Archief/) - Session handovers, old agent versions

---

## Summary

| Phase | Done | Total | Status |
|-------|------|-------|--------|
| Week 0: Foundation | 14 | 15 | 🔄 93% (1 DTO pending: ExecutionRequest) |
| Week 1: Config Schemas | 0 | 4 | 🔴 Not started |
| Week 2: Bootstrap | 0 | 3 | 🔴 Blocked |
| Week 3: Factories | 0 | 5 | 🔴 Blocked |
| Week 4: Platform | 0 | 4 | 🔴 Blocked |
| Technical Debt | 9 | 12 | 🔄 75% (3 items open) |

---

## 🚀 IMPLEMENTATION ROADMAP

> **For test counts and quality metrics:** See [IMPLEMENTATION_STATUS.md](implementation/IMPLEMENTATION_STATUS.md)

### Week 0: Foundation - ✅ COMPLETE

**Data Contracts (DTOs):**
- [x] Shared Layer: DispositionEnvelope, CausalityChain (Origin integration complete), PlatformDataDTO (Origin integration complete), Origin (NEW - type-safe origin tracking)
- [x] Signal/Risk Layer: Signal, Risk
- [x] Planning Layer: StrategyDirective, EntryPlan, SizePlan, ExitPlan, ExecutionPlan
- [ ] **ExecutionRequest DTO** - Payload for EXECUTION_INTENT_REQUESTED event
  - **Purpose:** Aggregated input for ExecutionIntentPlanner (3 parallel plans → execution plan)
  - **Fields:** trade_id, strategy_directive, entry_plan, size_plan, exit_plan, causality
  - **Location:** `backend/dtos/strategy/execution_request.py`
  - **Note:** Referenced in PIPELINE_FLOW.md but not yet implemented
- [x] Execution Layer: ExecutionCommand, ExecutionCommandBatch (combined in execution_command.py), ExecutionGroup

**Interface Protocols:**
- [x] IStrategyCache (protocol + implementation)
- [x] IEventBus (protocol + implementation)
- [x] IWorkerLifecycle (protocol)

**Platform Components:**
- [x] FlowInitiator - Per-strategy data ingestion and cache initialization (Phase 1.3)
  - **Implementation:** `backend/core/flow_initiator.py`
  - **Tests:** 14/14 passing (100% coverage)
  - **Quality:** Pylint 10/10
  - **Design:** [FLOW_INITIATOR_DESIGN.md](development/backend/core/FLOW_INITIATOR_DESIGN.md)
  - **Purpose:** Initialize StrategyCache before workers execute (race condition prevention)

**Metrics:** 395 tests passing (100% coverage) - See [IMPLEMENTATION_STATUS.md](implementation/IMPLEMENTATION_STATUS.md)

**Recent (2025-11-20):**
- **TradePlan DTO**: Implemented `TradePlan` (Execution Anchor) with `TPL_` prefix.
- **TradeStatus Enum**: Added `ACTIVE`/`CLOSED` status.
- **Quality**: 100% test coverage, 10/10 pylint.

**Recent (2025-11-09):**
- **Origin DTO complete** (16/16 tests) - Type-safe platform data origin tracking (TICK/NEWS/SCHEDULE)
- **PlatformDataDTO Origin integration** (19/19 tests, +5 tests) - Replaced source_type with origin field
- **CausalityChain Origin integration** (33/33 tests, +5 tests) - Replaced tick_id/news_id/schedule_id with origin field
- **Breaking changes:** PlatformDataDTO and CausalityChain consumers need updates
- CausalityChain execution tracking (order_ids/fill_ids) complete
- FlowInitiator implementation complete
- PlatformDataDTO refactored to minimal design (3 fields)

**Technical Debt:**
- [x] **Signal DTO: Remove causality field** (2025-11-09) **RESOLVED**
  - **Commit:** `91c3fb8` - refactor(signal): remove causality, rename asset→symbol
  - **Status:** COMPLETE - Signal is now PRE-CAUSALITY DTO
  - **Documentation:** DTO_ARCHITECTURE.md already updated (Signal is pre-causality)

- [x] **Risk DTO: Remove causality field** (2025-11-09) **RESOLVED**
  - **Commit:** `22f6b03` - refactor(risk): remove causality, rename affected_asset→affected_symbol
  - **Status:** COMPLETE - Risk is now PRE-CAUSALITY DTO
  - **Documentation:** DTO_ARCHITECTURE.md already updated (Risk is pre-causality)

- [x] **Symbol field naming consistency** (2025-11-09) **RESOLVED**
  - **Commits:** `91c3fb8` (Signal: asset→symbol), `22f6b03` (Risk: affected_asset→affected_symbol)
  - **Status:** COMPLETE - All DTOs now use `symbol` / `affected_symbol`
  - **Documentation:** DTO_ARCHITECTURE.md updated

- [x] **DirectiveScope: Align terminology with order-level operations** (2025-11-09) **REJECTED/CLOSED**
  - **UPDATE (2025-11-20):** REJECTED per Issue #7 architectural analysis
  - **Rationale:** StrategyPlanner operates on `TradePlan` level (Level 1), not Order level (Level 3)
  - **Decision:** Keep `MODIFY_EXISTING`/`CLOSE_EXISTING` - correct abstraction level
  - **Status:** CLOSED - No changes needed

- [x] **StrategyDirective: target_trade_ids → target_plan_ids** (2025-11-09) **RESOLVED**
  - **Commit:** `cb7c761` - feat(dto): rename target_trade_ids to target_plan_ids
  - **Status:** COMPLETE - Field renamed per Issue #7 recommendation
  - **Documentation:** Updated to match code SSOT

- [ ] **ExecutionGroup: Review `metadata` field usage** (2025-11-27)
  - **Issue:** `metadata: dict[str, Any]` is a code smell - suggests undefined structure
  - **Rationale:** Typed fields are preferable over generic dict; metadata implies "we don't know what goes here yet"
  - **Action:** Analyze actual usage patterns, define typed fields or remove if unused
  - **Scope:** backend/dtos/execution/execution_group.py
  - **Priority:** Medium (architectural clarity)

- [ ] **ExecutionDirective (sub-directive): REMOVE iceberg_preference field** (2025-12-02)
  - **Issue:** `iceberg_preference` field in `ExecutionDirective` (sub-directive) violates layer responsibilities
  - **Problem:** Iceberg execution is **ExecutionPlanner** responsibility, NOT StrategyPlanner
  - **Current violation:** `backend/dtos/strategy/strategy_directive.py` line 169 has `iceberg_preference: Decimal | None`
  - **Correct architecture:**
    - StrategyDirective.ExecutionDirective → only strategic hints (urgency, slippage limits)
    - ExecutionPlan → contains `visibility_preference: Decimal` (0.0=stealth, 1.0=visible)
    - ExecutionWorker → interprets visibility_preference for connector-specific execution
  - **Action Required:**
    1. Remove `iceberg_preference` from `ExecutionDirective` class
    2. Verify `ExecutionPlan` has `visibility_preference` field (already exists)
    3. Update tests that reference `iceberg_preference` in ExecutionDirective
  - **Scope:** backend/dtos/strategy/strategy_directive.py (ExecutionDirective class)
  - **Priority:** High (architectural violation)

- [x] **DTO_ARCHITECTURE.md: Major sync with authoritative docs** (2025-12-03) ✅ COMPLETED
  - **Completed:** 2025-11-28
  - **Final Version:** 1.2 (Status: DEFINITIVE)
  - **Current Length:** 1475 lines (compression deferred to separate task)
  
  **Commits:**
  - `e60000b` - Phase 1: Remove ExecutionTranslator references
  - `d671ae7` - Phase 2: EXECUTION_FLOW.md alignment (ExecutionWorker, StrategyJournalWriter, CausalityChain)
  - `70246a5` - Phase 3: PIPELINE_FLOW.md alignment (DirectiveScope values)
  - `4c16347` - Phases 4-5: WORKER_TAXONOMY.md + TRADE_LIFECYCLE.md verified
  - `40463fe` - Phase 8: Version History, DEFINITIVE status
  
  **Deferred to Separate Task:**
  - Document compression (1475 lines → target <1000)
  - Numbered sections (## 1., ### 1.1.)
  - Move Design Decisions to development docs
  
  <details>
  <summary>📋 Original Analysis & Authoritative Sources (click to expand)</summary>
  
  **Authoritative Sources (SSOT - Single Source of Truth):**
  | Document | Last Updated | Status |
  |----------|--------------|--------|
  | EXECUTION_FLOW.md | 2025-11-27 | ✅ CORRECT |
  | PIPELINE_FLOW.md | 2025-11-28 | ✅ CORRECT |
  | WORKER_TAXONOMY.md | 2025-11-27 | ✅ CORRECT |
  | TRADE_LIFECYCLE.md | 2025-11-27 | ✅ CORRECT |
  | Code (backend/dtos/) | Current | ✅ SSOT |
  
  **DOCUMENTATION REQUIREMENTS (per DOCUMENTATION_MAINTENANCE.md):**
  - **Max Lines:** 1000 (Architecture docs) - Currently 1359 → MUST REDUCE
  - **Template:** ARCHITECTURE_TEMPLATE.md applies
  - **Numbered Sections:** Required (## 1., ### 1.1.)
  - **Mermaid Diagrams:** For visualization
  - **NO Implementation Code:** Link to source files
  - **Focus:** WHAT and WHY, not HOW
  - **Cross-References:** Link, don't duplicate (Single Source of Truth)
  - **Status Lifecycle:** DRAFT → PRELIMINARY → APPROVED → DEFINITIVE
  
  **REFACTORING PLAN:**
  
  ### Phase 0: Structure Analysis & Compression Strategy
  - [ ] **Analyze current structure** (1359 lines - 359 over limit)
    - Platform DTOs: Origin, PlatformDataDTO (~130 lines)
    - Analysis DTOs: Signal, Risk, StrategyDirective (~380 lines)
    - Planning DTOs: EntryPlan, SizePlan, ExitPlan, ExecutionPlan (~370 lines)
    - Execution DTOs: ExecutionCommand, ExecutionCommandBatch, ExecutionGroup (~400 lines)
    - Cross-Cutting: CausalityChain, DispositionEnvelope (~80 lines?)
  - [ ] **Decide compression strategy:**
    - Option A: Compress "WHY NOT included" and verbose rationale sections
    - Option B: Move detailed field rationale to docs/development/backend/dtos/ design docs
    - Option C: Split into multiple architecture docs (last resort)
  - [ ] **Apply ARCHITECTURE_TEMPLATE structure**
  
  ### Phase 1: Remove Non-Existent Components ✅ COMPLETED
  - [x] **Removed ExecutionTranslator from all active docs** (2025-XX-XX)
    - DTO_ARCHITECTURE.md: 8 occurrences replaced
    - execution_plan.py: docstrings updated (lines 20, 47, 53-54)
    - EXECUTION_PLAN_DESIGN.md: translation pattern updated
    - PLANNING_AGGREGATOR_DESIGN.md: responsibilities updated
    - SCENARIO_MODIFICATION_FLOWS.md: terminology updated
    - SCENARIO_TRAILING_STOP.md: terminology updated
    - PLATFORM_VS_STRATEGY_WIRING.md: 8 occurrences replaced
    - Trade Lifecycle & Architectuur.md: 7 occurrences replaced
  - [x] **Preserved archive references** (intentionally kept for historical context)
    - docs/archive/PIPELINE_FLOW_v4_deprecated.md
    - docs/development/#Archief/* 
    - docs/development/251108_1530 ChatLog.md
  
  ### Phase 2: Align with EXECUTION_FLOW.md ✅ COMPLETED
  - [x] **Verified ExecutionPlanner role** (4th TradePlanner, read-only Ledger)
  - [x] **Updated ExecutionHandler → ExecutionWorker** (20+ occurrences aligned with WORKER_TAXONOMY.md)
  - [x] **Added StrategyJournalWriter references** (replaced "Journal" in Producer/Consumer tables)
  - [x] **Documented ID propagation pattern** (added full pattern to CausalityChain section)
  - [x] **Added CausalityChain documentation** (complete Cross-Cutting DTOs section)
  - [x] **Updated cross-references** (added WORKER_TAXONOMY.md, TRADE_LIFECYCLE.md links)
  - [x] **Updated version/date** (1.1, 2025-11-28)
  
  ### Phase 3: Align with PIPELINE_FLOW.md ✅ COMPLETED
  - [x] **Fixed DirectiveScope values** (MODIFY_ORDER/CLOSE_ORDER → MODIFY_EXISTING/CLOSE_EXISTING)
  - [x] **Fixed target_order_ids → target_plan_ids** (aligns with code SSOT in enums.py)
  - [x] **Verified phase descriptions** (Phase 3 StrategyDirective, Phase 4 TradePlanners, Phase 5 ExecutionWorker)
  - [x] **Fixed sub-directive naming** (routing → execution in scope semantics table)
  
  ### Phase 4: Align with WORKER_TAXONOMY.md ✅ VERIFIED
  - [x] **6 worker categories match Producer/Consumer tables:**
    - ContextWorker: Stores to StrategyCache (not in DTO_ARCH, correct - produces plugin DTOs)
    - SignalDetector: Producer for Signal DTO (7 references)
    - RiskMonitor: Producer for Risk DTO (8 references)
    - PlanningWorker: Producers for Plan DTOs (Entry/Size/Exit/ExecutionPlan)
    - StrategyPlanner: Producer for StrategyDirective
    - ExecutionWorker: Producer/Consumer for ExecutionGroup (self-updating, no EventBus output)
  
  ### Phase 5: Align with TRADE_LIFECYCLE.md ✅ VERIFIED
  - [x] **Container hierarchy documented:** TradePlan → ExecutionGroup → Order → Fill
  - [x] **Ledger access patterns:** DTO_ARCHITECTURE correctly describes ExecutionWorker full CRUD
  - [x] **ExecutionAction enum matches code:** EXECUTE_TRADE, CANCEL_ORDER, MODIFY_ORDER, CANCEL_GROUP
    - Note: TRADE_LIFECYCLE.md has outdated values (CANCEL_ALL_IN_PLAN, MODIFY_ORDERS) - separate fix
  - [x] **DirectiveScope matches code:** NEW_TRADE, MODIFY_EXISTING, CLOSE_EXISTING (fixed in Phase 3)
  
  ### Phase 6: Code SSOT Verification ✅ VERIFIED
  - [x] **All pipeline DTOs documented:** Origin, PlatformDataDTO, Signal, Risk, StrategyDirective, 
        EntryPlan, SizePlan, ExitPlan, ExecutionPlan, ExecutionCommand, ExecutionCommandBatch, ExecutionGroup
  - [x] **Cross-cutting DTOs added:** CausalityChain, DispositionEnvelope (Phase 2)
  - [x] **State DTOs (TradePlan, Order, Fill):** OUT OF SCOPE
    - These are "container" DTOs, not pipeline DTOs
    - Already documented in TRADE_LIFECYCLE.md (container hierarchy)
    - Adding them would exceed 1000 line limit (currently 1466 lines)
  - [x] **ExecutionRequest rejected section:** Kept in Appendix A as historical context
  
  ### Phase 7: Documentation Compliance ⚠️ PARTIAL
  - [x] **Header:** Status, Version (1.1), Last Updated (2025-11-28) ✅
  - [x] **Purpose section:** Present in Executive Summary ✅
  - [x] **Cross-references:** Added in Phase 2 (WORKER_TAXONOMY.md, TRADE_LIFECYCLE.md) ✅
  - [ ] **1000 LINE LIMIT EXCEEDED:** Currently 1465 lines (limit: 300-1000)
    - Compression options for future:
      - Move "Design Decisions" to development/backend/dtos/ design docs
      - Compress "WHY NOT included" rationale sections
      - Move "Validation Strategy" details to code docstrings
  - [ ] **Numbered sections not applied** (## 1., ### 1.1.) - cosmetic, low priority
  - [ ] **Version History section missing** - should add
  
  ### Phase 8: Final Cleanup ✅ COMPLETED
  - [x] **Last Updated:** 2025-11-28
  - [x] **Version:** 1.2 (added Version History section)
  - [x] **Status:** DEFINITIVE (reflects validated state)
  - [x] **Version History:** Added with full changelog
  
  **Document Length:** 1475 lines (exceeds 1000 limit - compression deferred to separate task)
  
  **Commits:**
  - `e60000b` - Phase 1: Remove ExecutionTranslator references
  - `d671ae7` - Phase 2: EXECUTION_FLOW.md alignment
  - `70246a5` - Phase 3: PIPELINE_FLOW.md alignment
  - `4c16347` - Phases 4-5: WORKER_TAXONOMY.md + TRADE_LIFECYCLE.md verified
  
  **Deferred:**
  - Document compression (move Design Decisions to dev docs)
  - Numbered sections (## 1., ### 1.1.) per ARCHITECTURE_TEMPLATE.md
  
  **Scope:** docs/architecture/DTO_ARCHITECTURE.md + backend/dtos/strategy/execution_plan.py
  **Priority:** High (documentation out of sync with reality)
  **Completed:** 2025-11-28
  
  </details>

- [x] **ExecutionStrategyType: Remove DCA from enum** (2025-11-27) **RESOLVED**
  - **Commit:** `3b45af6` - refactor(dto): remove DCA from ExecutionStrategyType enum
  - **Status:** COMPLETE - DCA is now correctly a planning-level concept
  - **Scope:** ExecutionStrategyType enum now has: SINGLE, TWAP, VWAP, ICEBERG, LAYERED, POV

- [x] **StrategyDirective sub-directive: ExecutionDirective** (2025-11-09) **RESOLVED**
  - **Code SSOT:** `backend/dtos/strategy/strategy_directive.py` line 148 - `ExecutionDirective` class
  - **Field:** `execution_directive: ExecutionDirective | None`
  - **Consumer:** ExecutionPlanner (4th TradePlanner)
  - **Resolution:** 
    - ExecutionDirective (execution layer) → **ExecutionCommand** (EXC_ prefix)
    - ExecutionDirectiveBatch → **ExecutionCommandBatch** (combined in execution_command.py)
    - No naming conflict - sub-directive remains `ExecutionDirective`
  - **Status:** COMPLETE (Dec 2025)
  - **Documentation:** Updated to match code SSOT

- [x] **Asset format: BASE/QUOTE → BASE_QUOTE** (2025-11-09) **RESOLVED**
  - **Status:** COMPLETE - All DTOs use underscore format (e.g., BTC_USDT)
  - **Verification:** Signal examples show `symbol="BTC_USDT"` format
  - **Documentation:** DTO_ARCHITECTURE.md already updated

- [x] **Enums Centralisatie** (2025-11-09) **RESOLVED**
  - **Commit:** `39f12bc` - refactor: centralize enums to backend/core/enums.py (Phase 4.2)
  - **Status:** COMPLETE - All enums now in `backend/core/enums.py`
  - **Includes:** OriginType, DirectiveScope, ExecutionMode, ExecutionAction, ExecutionStrategyType, GroupStatus, OrderType, OrderSide, OrderStatus, DispositionType, etc.

- [x] **TickCache → StrategyCache Rename** (2025-11-27) **RESOLVED**
  - **Issue:** `TickCache` terminology was outdated and confusing - suggested only tick data storage
  - **Solution:** Renamed all references to `StrategyCache` in leidende docs
  - **Scope Completed:**
    - ✅ All leidende architecture docs updated (PLATFORM_COMPONENTS, PIPELINE_FLOW, DATA_FLOW, etc.)
    - ✅ Code already used `StrategyCache` (interface `IStrategyCache`)
    - ⚠️ ARCHITECTURE_GAPS.md still has `TickCache` (niet-leidend document)
  - **Status:** COMPLETE (Dec 2025)

---

### Week 1: Configuration Schemas - 🔥 IN PROGRESS (CRITICAL PATH)

**Status:** BLOCKER voor ALLES  
**Location:** `backend/config/schemas/` + `tests/unit/config/`

**Config Schemas (Pydantic models, NOT DTOs):**
- [ ] worker_manifest_schema.py → WorkerManifest, SchemaReference
- [ ] wiring_config_schema.py → EventWiring, WiringConfig
- [ ] strategy_blueprint_schema.py → Workforce, StrategyBlueprint
- [ ] buildspec_schemas.py → WorkerBuildSpec, WiringBuildSpec, StrategyBuildSpec

**Deliverable:** Config schema contracts validated (target: 60+ tests)

---

### Week 2: Bootstrap Components - Config Pipeline

**Dependencies:** Week 1 Config Schemas  
**Location:** `backend/config/` (ConfigLoader, ConfigValidator, ConfigTranslator)

**Components:**
- [ ] ConfigLoader (YAML → Pydantic models)
- [ ] ConfigValidator (handler validation, params, circular dependencies)
- [ ] ConfigTranslator (Config → BuildSpecs)

**Deliverable:** YAML → BuildSpecs pipeline working (target: 80+ tests)

---

### Week 3: Factories - Assembly Infrastructure

**Dependencies:** Week 1 (Schemas) + Week 2 (Bootstrap)  
**Location:** `backend/assembly/` or `backend/config/`

**Factories:**
- [ ] PluginRegistry (plugin discovery & loading)
- [ ] WorkerFactory (worker instantiation from BuildSpecs)
- [ ] EventWiringFactory (EventAdapter assembly from BuildSpecs)
- [ ] StrategyFactory (complete strategy orchestration)
- [ ] **WorkerMetadataRegistry** (runtime registry for manifest metadata)
  - **Purpose:** Enable StrategyCache DTO validation without manifest parsing at runtime
  - **Built during bootstrap:** PluginRegistry → ConfigTranslator → Factory → Registry
  - **Contains:** WorkerMetadata (produces_dtos, requires_dtos, scope) per worker
  - **Usage:** O(1) lookups for runtime validation (defense-in-depth)
  - **Design doc:** `docs/development/backend/core/WORKER_METADATA_REGISTRY_DESIGN.md`

**Deliverable:** Complete strategy assembly from BuildSpecs + runtime metadata registry (target: 70+ tests)

---

### Week 4: Platform Components - Event Infrastructure

**Dependencies:** Week 3 (Factories)  
**Location:** `backend/core/` and platform-specific modules

**Components:**
- [ ] EventAdapter (bus-agnostic worker wrapper)
- [ ] FlowCoordinator (run lifecycle orchestration) - Was: TickCacheManager (name deprecated)
- [ ] PlanningAggregator (4-plan coordinator, mode-aware)
  - **Design doc:** `docs/development/backend/core/PLANNING_AGGREGATOR_DESIGN.md`
  - **Purpose:** Multi-input aggregator for Entry/Size/Exit/Execution plans
  - **Pattern:** Fan-in coordination (5 event handlers → 2 output events)
  - **State:** Per-trade tracking matrix with RunAnchor reentry guard
  - **Output:** EXECUTION_INTENT_REQUESTED, EXECUTION_COMMAND_BATCH_READY
- [ ] **StrategyCache Runtime Validation** (optional defense-in-depth)
  - **Purpose:** Validate worker DTO contracts at runtime (catch implementation bugs)
  - **Dependencies:** WorkerMetadataRegistry (Week 3)
  - **Implementation:** Update `set_result_dto()` / `get_required_dtos()` with optional validation
  - **Strategy:** Fail-fast in dev, silent/logging in production
  - **Validation checks:** Worker produces expected DTOs, requests only declared DTOs

**Open Design Issues:**
- [ ] **Issue #5: TradePlan in CausalityChain** (BLOCKER for PlanningAggregator)
  - **Question:** How and when is the TradePlan included in the CausalityChain?
  - **Context:** With `target_plan_ids` in StrategyDirective, we know which plans are targeted. But we need to track the *creation* and *lifecycle* of plans in the chain.
  - **Status:** Open question. Defer decision until PlanningAggregator implementation.
  - **Note:** CausalityChain currently lacks trade/batch tracking mechanism

- [ ] **Issue #6: ExecutionCommandBatch execution_mode Decision Logic** (2025-11-09)
  - **Problem:** PlanningAggregator currently hardcodes execution_mode=ATOMIC for ALL batches (SRP violation)
  - **Current State:** 
    - PlanningAggregator sets execution_mode, timeout_seconds, rollback_on_failure with hardcoded defaults
    - StrategyDirective contains execution signals (scope, confidence, execution_directive.execution_urgency)
    - No documented algorithm for WHEN to use SEQUENTIAL vs PARALLEL vs ATOMIC
  - **Field Duplication Issue:**
    - ExecutionPlan.max_execution_window_minutes (per-command, from ExecutionPlanner)
    - ExecutionCommandBatch.timeout_seconds (batch-level, from PlanningAggregator)
    - Potential conflict: command wants 60min, batch allows 30s
  - **Use Cases Identified (from DTO examples):**
    - ATOMIC: Flash crash emergency exit (scope=CLOSE_EXISTING, urgency=1.0, rollback=True)
    - SEQUENTIAL: Hedged exit with ordering (close hedge FIRST, then main position, count=2)
    - PARALLEL: Bulk order modifications (scope=MODIFY_EXISTING, independent operations, best-effort)
  - **Research Questions:**
    1. WHO determines execution_mode? (StrategyPlanner vs PlanningAggregator vs derived from inputs)
    2. WHEN to use each mode? (document decision algorithm/triggers)
    3. Should StrategyDirective have execution_policy field? (batch coordination strategy)
    4. Field ownership: Keep both timeouts or consolidate? (relationship between plan and batch timeouts)
  - **Potential Solution:** Derive execution_mode from StrategyDirective fields:
    - `scope` (NEW_TRADE / MODIFY_EXISTING / CLOSE_EXISTING)
    - `confidence` [0.0-1.0]
    - `execution_directive.execution_urgency` [0.0-1.0]
    - Directive count (1 vs multiple)
  - **Impact:** Affects PlanningAggregator implementation, ExecutionCommandBatch field rationale
  - **Priority:** High (architectural correctness - SRP, field ownership clarity)
  - **Related Docs:** 
    - `docs/architecture/DTO_ARCHITECTURE.md` (ExecutionCommandBatch documentation)
    - `docs/development/backend/core/PLANNING_AGGREGATOR_DESIGN.md` (line 389: hardcoded defaults)
  - **Next Steps:** Research and document decision algorithm before PlanningAggregator implementation

- [ ] **Issue #7: StrategyDirective Architecture Refactor** (2025-11-20)
  - **Context:** Deep dive into StrategyPlanner role revealed architectural misalignment in previous TODOs.
  - **Core Principle:** StrategyPlanner (Level 1) operates on `TradePlan` (Intent), not `Order` (Implementation).
  - **Changes Required:**
    1.  **Rename `target_trade_ids` → `target_plan_ids`** (Fixes abstraction leak). ✅ **DONE**
    2.  ~~**Rename `ExecutionDirective` (sub-directive) → `RoutingDirective`**~~ **RESOLVED** - Naming conflict fixed by renaming execution layer class to ExecutionCommand.
    3.  **Rename `position_size` → `target_position_size`** (Enforces absolute target semantics).
    4.  **Reject `MODIFY_ORDER` rename** (Keep `MODIFY_EXISTING` to respect Level 1 abstraction).
  - **Impact:** BREAKING CHANGE - affects StrategyDirective, SizeDirective, SizePlan, and all StrategyPlanners.
  - **Validation:** Validated via:
    - `docs/development/design_validations/SCENARIO_MODIFICATION_FLOWS.md`
    - `docs/development/design_validations/SCENARIO_TRAILING_STOP.md`
    - `docs/development/design_validations/LONG_SHORT_TARGET_SIZE_VALIDATION.md`
    - `docs/development/design_validations/STRATEGY_CARDINALITY_ANALYSIS.md`

**Deliverable:** Core platform components implemented & integrated (target: 70+ tests)

---

### Week 5: Base Workers - Worker Foundation

**Dependencies:** Week 4 (Platform Components)  
**Location:** `backend/workers/base/`

**Workers:**
- [ ] BaseWorker (abstract foundation, IWorkerLifecycle implementation)
- [ ] ContextWorker, SignalDetector, RiskMonitor
- [ ] StrategyPlanner, PlanningWorker (Entry/Size/Exit/Execution)

**Deliverable:** Worker foundation with DispositionEnvelope integration (target: 40+ tests)

---

### Week 6: Orchestration - Execution Flow

**Dependencies:** Week 5 (Base Workers)  
**Location:** `backend/orchestration/` or `backend/core/`

**Components:**
- [ ] StrategyRunner (main execution loop, tick processing)
- [ ] Error handling & edge cases

**Deliverable:** End-to-end tick processing working (target: 30+ tests)

---

### Week 7: Integration & Polish - Production Ready

**Dependencies:** Week 6 (Orchestration)

**Components:**
- [ ] OperationService (strategy lifecycle management)
- [ ] End-to-end integration tests (YAML → Execution → Results)
- [ ] Multi-strategy scenarios
- [ ] Error handling & edge cases

**Deliverable:** Production-ready platform, full bootstrap from YAML to execution

---

## 📋 Architectural Decisions & Design Notes

> **Voor complete design docs:** Zie `docs/development/` en `docs/architecture/`

### Key Decisions

**Config Schema Naming (2025-10-30):**
- ✅ `*_schema.py` files (NOT `*_dto.py`)
- ✅ Class names WITHOUT "DTO" suffix (WorkerManifest, not WorkerManifestDTO)
- ✅ Rationale: Config schemas are validation contracts, not runtime data DTOs
- ✅ Location: `backend/config/schemas/`

**Implementation Order (2025-10-30):**
- Config Schemas FIRST (Week 1) - critical blocker for everything
- Bootstrap & Factories depend on schemas
- Platform Components depend on Factories (EventWiringFactory needs BuildSpecs)
- Workers depend on Platform Components

**Documentation Responsibility (2025-10-30):**
- TODO.md: Task status, checkboxes, chronological roadmap (THIS FILE)
- IMPLEMENTATION_STATUS.md: Quality metrics, test counts, coverage stats (SRP)

### Design Documents

**Active Designs:**
- [EVENTADAPTER_DESIGN.md](development/EVENTADAPTER_DESIGN.md) - EventAdapter architecture
- [CONFIG_BUILDSPEC_TRANSLATION_DESIGN.md](development/CONFIG_BUILDSPEC_TRANSLATION_DESIGN.md) - Config pipeline
- [BASEWORKER_DESIGN_PRELIM.md](development/BASEWORKER_DESIGN_PRELIM.md) - Worker foundation
- [DATA_PROVIDER_DESIGN.md](development/backend/core/DATA_PROVIDER_DESIGN.md) - DataProvider architecture
- [FLOW_INITIATOR_DESIGN.md](development/backend/core/FLOW_INITIATOR_DESIGN.md) - ✅ FlowInitiator implementation (Phase 1.3 Complete)
- **[WORKER_METADATA_REGISTRY_DESIGN.md](development/backend/core/WORKER_METADATA_REGISTRY_DESIGN.md)** - Runtime metadata registry (PENDING)

**Architecture Guides:**
- [LAYERED_ARCHITECTURE.md](architecture/LAYERED_ARCHITECTURE.md) - System layers
- [EVENT_DRIVEN_WIRING.md](architecture/EVENT_DRIVEN_WIRING.md) - Event orchestration
- [PLUGIN_ANATOMY.md](architecture/PLUGIN_ANATOMY.md) - Plugin structure
- [WORKER_TAXONOMY.md](architecture/WORKER_TAXONOMY.md) - Worker types & responsibilities

---

## 🎯 Next Actions

**Current Week:** Week 1 - Configuration Schemas

**Next Task:** Implement `worker_manifest_schema.py`
- Start feature branch: `feature/config-schemas-week1`
- TDD: Write 20+ tests first (RED phase)
- Implement WorkerManifest + SchemaReference (GREEN phase)
- Quality gates: Pylint 10/10, all tests passing
- See: [TDD_WORKFLOW.md](coding_standards/TDD_WORKFLOW.md)

**After Week 1:** ConfigLoader, ConfigValidator, ConfigTranslator (Week 2)

---

**Last Updated:** 2025-11-09  
**Maintained By:** Development Team  
**Review Frequency:** Weekly
