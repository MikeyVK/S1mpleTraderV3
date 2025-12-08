# SimpleTraderV3 - Implementation TODO

**Status:** LIVING DOCUMENT  
**Last Updated:** 2025-12-04  
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
| [TODO_COMPLETED.md](archive/TODO_COMPLETED.md) | Archived completed tasks |

**Navigation:**
- **📖 Agent Instructions:** [../agent.md](../agent.md) - AI assistant guide
- **🏛️ Architecture:** [architecture/README.md](architecture/README.md) - System design
- **✨ Coding Standards:** [coding_standards/README.md](coding_standards/README.md) - TDD, quality gates
- **📋 Reference:** [reference/README.md](reference/README.md) - Templates

---

## Summary

| Phase | Done | Total | Status |
|-------|------|-------|--------|
| Week 0: Foundation | 14 | 15 | 🔄 93% (1 DTO pending) |
| Week 1: Config Schemas | 0 | 4 | 🔴 Not started |
| Week 2: Bootstrap | 0 | 3 | 🔴 Blocked |
| Week 3: Factories | 0 | 5 | 🔴 Blocked |
| Week 4: Platform | 0 | 4 | 🔴 Blocked |
| Technical Debt | 8 | 13 | 🔄 62% (8 DTOs verified) |

---

## 🚀 IMPLEMENTATION ROADMAP

> **For test counts and quality metrics:** See [IMPLEMENTATION_STATUS.md](implementation/IMPLEMENTATION_STATUS.md)

### Week 0: Foundation - ✅ COMPLETE

**Status:** 93% complete (456 tests passing)  
**Archive:** See [TODO_COMPLETED.md](archive/TODO_COMPLETED.md) for details

**Remaining:**
- [ ] **ExecutionRequest DTO** - Payload for EXECUTION_INTENT_REQUESTED event
  - **Purpose:** Aggregated input for ExecutionIntentPlanner
  - **Location:** `backend/dtos/strategy/execution_request.py`

---

## 🔧 Technical Debt

### Open Items

- [x] **Signal DTO: Already Compliant** (2025-12-07) ✅
  - **Source:** `docs/development/backend/dtos/SIGNAL_DESIGN.md`
  - **Status:** ✅ Verified compliant - no changes needed
  - **Verification:** 32 tests passing, 0 type errors
  - **All items already implemented:**
    - [x] No `causality` field (pre-causality DTO)
    - [x] Uses `symbol` (not `asset`)
    - [x] Symbol pattern `BTC_USDT` (underscore separator)
    - [x] `confidence: Decimal` type

- [x] **Risk DTO: Already Compliant** (2025-12-07) ✅
  - **Source:** `docs/development/backend/dtos/RISK_DESIGN.md`
  - **Status:** ✅ Verified compliant - no changes needed
  - **Verification:** 29 tests passing, 0 type errors
  - **All items already implemented:**
    - [x] No `causality` field (pre-causality DTO)
    - [x] Uses `affected_symbol` (not `affected_asset`)
    - [x] Symbol pattern `BTC_USDT` (underscore separator)
    - [x] `severity: Decimal` type

- [ ] **Order DTO: Not Implemented** (2025-12-07)
  - **Source:** `docs/development/backend/dtos/ORDER_DESIGN.md`
  - **Status:** ❌ Not Implemented
  - **Prerequisites:**
    - [ ] Add `generate_order_id()` to `backend/utils/id_generators.py`
    - [ ] Add `OrderType`, `OrderStatus` enums to `backend/core/enums.py`
  - **Implementation:**
    - [ ] Create `backend/dtos/state/order.py`
    - [ ] Write tests and verify passing

- [ ] **Fill DTO: Not Implemented** (2025-12-07)
  - **Source:** `docs/development/backend/dtos/FILL_DESIGN.md`
  - **Status:** ❌ Not Implemented
  - **Prerequisites:**
    - [ ] Implement Order DTO first (Fill references Order)
    - [ ] Add `generate_fill_id()` to `backend/utils/id_generators.py`
  - **Implementation:**
    - [ ] Create `backend/dtos/state/fill.py`
    - [ ] Write tests and verify passing

- [x] **ExecutionGroup: DCA already removed** (2025-12-07) ✅
  - **Source:** `docs/development/backend/dtos/EXECUTION_GROUP_DESIGN.md`
  - **Status:** ✅ Verified - DCA removed in commit `3b45af6`
  - **Verification:** Enum contains SINGLE, TWAP, VWAP, ICEBERG, LAYERED, POV (no DCA)

- [x] **StrategyDirective: Code Verified + ExecutionPolicy Added** (2025-12-07) ✅
  - **Source:** `docs/development/backend/dtos/STRATEGY_DIRECTIVE_DESIGN.md`
  - **Status:** ✅ Code verified - 30 tests passing, 0 type errors
  - **Verified:**
    - [x] Field uses `target_plan_ids` (not `target_trade_ids`)
    - [x] CODE_STYLE.md compliance
    - [x] pytest: 30 tests passing
    - [x] pyright: 0 errors
  
  - **🏛️ Architecture Decisions (implemented 2025-12-07):**
    - [x] **Mutability:** Changed to `frozen=True` (immutable).
      - StrategyDirective is a decision record - decisions don't change
      - Removed `validate_assignment=True` (not needed with frozen)
    - [x] **Enrichment/SRP:** No order_ids in StrategyDirective (verified in code)
      - Orders/fills belong in StrategyLedger, not StrategyDirective
    - [x] **Lifecycle:** StrategyDirective is never deleted, only persisted to Journal
      - Created → consumed by Planners → aggregated to ExecutionCommand → persisted
    - [x] **ExecutionPolicy:** NEW field for batch coordination (implemented 2025-12-07)
      - Added `execution_policy: ExecutionPolicy | None` field
      - ExecutionPolicy contains: `mode` (BatchExecutionMode) + `timeout_seconds`
      - 1:1 mapping to ExecutionCommandBatch (dumb pipe, no logic)
      - See: `EXECUTION_COMMAND_BATCH_DESIGN.md` Section 8
  
  - **Completed Implementation:**
    - [x] Change `frozen=False` → `frozen=True`
    - [x] Remove `validate_assignment=True` from model_config
    - [x] Add `ExecutionPolicy` class (before StrategyDirective in same file)
    - [x] Add `execution_policy: ExecutionPolicy | None = None` field
    - [x] Add `BatchExecutionMode` enum to `backend/core/enums.py`
    - [x] Update tests for immutability (4 new tests)
    - [x] Update tests for ExecutionPolicy field (9 new tests)
    - [x] Export `ExecutionPolicy` from `backend/dtos/strategy/__init__.py`
  
  - **Documentation Issues (pending after implementation):**
    - [ ] **"WHY this DTO exists" Cleanup:**
      - Remove DRY violation (scope field types duplicated)
      - Replace "Routing" → "Execution" terminology
    - [ ] **Confidence Field Rationale is WRONG:**
      - Current (wrong): "Low confidence = skip or reduce size"
      - Correct: confidence for planner TYPE selection (aggressive vs conservative)
    - [ ] **MODIFY_EXISTING Scope Incomplete:**
      - Update Scope Semantics table to include entry plan modifications

- [x] **TradePlan: Quality gates passed** (2025-12-07) ✅
  - **Source:** `docs/development/backend/dtos/TRADE_PLAN_DESIGN.md`
  - **Status:** ✅ Verified
  - **Verification:**
    - [x] pytest: 4 tests passing
    - [x] pyright: 0 errors

- [x] **PlatformDataDTO: Quality gates passed** (2025-12-07) ✅
  - **Source:** `docs/development/backend/dtos/PLATFORM_DATA_DTO_DESIGN.md`
  - **Status:** ✅ Verified
  - **Verification:**
    - [x] pytest: 19 tests passing
    - [x] pyright: 0 errors

- [ ] **ExecutionCommand: CausalityChain field TBD** (2025-12-07)
  - **Source:** `docs/development/backend/dtos/EXECUTION_COMMAND_DESIGN.md`
  - **Pending:** `execution_directive_id` → `execution_command_id` in CausalityChain (TBD when needed)
  - **Documentation Issues (from DTO_ARCHITECTURE.md review):**
    - [ ] **Definition Clarification:**
      - Current: "Final aggregated execution instruction"
      - Proposed: "Aggregated plans which form a complete execution instruction"
      - Emphasize: aggregation of Entry/Size/Exit/ExecutionPlan into single command
    - [ ] **PlanningAggregator Terminology Still Present:**
      - Replace PlanningAggregator references with correct location
      - Aggregation happens in BaseExecutionPlanner boilerplate code
    - [ ] **Plan Validation Responsibility Unclear:**
      - Decision needed: BaseWorker validates structure OR ExecutionWorker validates content?
      - Content validation = business logic, structure validation = DTO integrity

- [ ] **ExecutionCommandBatch: Field Origin & Metadata** (2025-12-07) 🔄 PARTIALLY IMPLEMENTED
  - **Source:** `docs/development/backend/dtos/EXECUTION_COMMAND_BATCH_DESIGN.md`
  - **🏛️ Architecture Decision (2025-12-07):**
    - **ExecutionPolicy in StrategyDirective:** ✅ IMPLEMENTED
    - **1:1 Mapping:** StrategyDirective ↔ ExecutionCommandBatch (één directive = één batch)
    - **Dumb Pipe Aggregatie:** Boilerplate code kopieert velden 1-op-1, geen logica
    - **BatchExecutionMode Enum:** ✅ IMPLEMENTED - INDEPENDENT (default), COORDINATED, SEQUENTIAL
  - **Completed:**
    - [x] Create `ExecutionPolicy` class in `strategy_directive.py`
    - [x] Add `execution_policy: ExecutionPolicy | None` to `StrategyDirective`
    - [x] Add `BatchExecutionMode` enum to `backend/core/enums.py`
  
  - **🏛️ Architecture Decision: ExecutionMode → BatchExecutionMode (2025-12-08):**
    - **Besluit:** Legacy `ExecutionMode` enum wordt volledig vervangen door `BatchExecutionMode`
    - **Rationale:**
      1. **Strategisch vs Technisch:** `BatchExecutionMode` drukt strategische intentie uit (relatie tussen orders), niet technische implementatie (threading model). Strategy layer hoort geen implementatiedetails te dicteren.
      2. **ATOMIC is oneerlijk:** Trading kent geen echte rollback - een gevulde order kan niet "un-filled" worden. `COORDINATED` is eerlijker: het belooft "cancel pending", niet "rollback filled".
      3. **PARALLEL vs INDEPENDENT:** `PARALLEL` is implementatiedetail (asyncio). `INDEPENDENT` is intentie ("falen van A boeit B niet"). ExecutionHandler bepaalt HOE (parallel/sequential), niet de DTO.
    - **Mapping semantiek (DTO-niveau, geen implementatiedetails):**
      - `INDEPENDENT` → Orders zijn onafhankelijk, individuele failures stoppen de batch niet
      - `COORDINATED` → Orders zijn gerelateerd, failure triggert cancel van pending orders
      - `SEQUENTIAL` → Volgorde is cruciaal, failure stopt verdere uitvoering
    - **Impact:** 26 usages in ExecutionCommandBatch + tests moeten migreren
  
  - **Remaining Implementation (in volgorde):**
    - [ ] **Step 1: Design doc update** - EXECUTION_COMMAND_BATCH_DESIGN.md met enum besluit
    - [ ] **Step 2: Remove legacy enum** - Verwijder `ExecutionMode` uit `backend/core/enums.py`
    - [ ] **Step 3: Refactor ExecutionCommandBatch:**
      - Rename `execution_mode` → `mode`
      - Change type to `BatchExecutionMode`
      - Remove `rollback_on_failure` (implicit in mode definition)
      - Remove `metadata: dict[str, Any]`
    - [ ] **Step 4: Update tests** - Migreer alle 20+ tests naar nieuwe structuur
    - [ ] **Step 5: Update DTO_ARCHITECTURE.md** - Nieuwe flow documenteren
  - **Design Document:** `docs/development/backend/dtos/EXECUTION_COMMAND_BATCH_DESIGN.md`

- [ ] **ExecutionPlan: Architecture Overhaul** (2025-12-07) 🔴 HIGH
  - **Source:** `docs/development/backend/dtos/EXECUTION_PLAN_DESIGN.md`
  - **Documentation Issues (from DTO_ARCHITECTURE.md review):**
    - [ ] **Output Should Be Concrete Strategy, NOT Trade-offs:**
      - Current (wrong): "universal trade-offs" (urgency, visibility preferences)
      - Correct: concrete execution strategy (TWAP, ICEBERG, SINGLE)
      - ExecutionPlanner decides based on ExecutionDirective + confidence
    - [ ] **"WHY this DTO exists" Point 4 is WRONG:**
      - Wrong: "Translation layer converts ExecutionPlan → connector-specific specs"
      - Correct flow (5 steps):
        1. ExecutionPlan is executed by ExecutionWorker
        2. ExecutionWorker handles ALL Ledger interaction
        3. ExecutionWorker creates individual Orders
        4. Orders passed to IExecutionConnector in ExecutionEnvironment
        5. IExecutionConnector does exchange translation (CEX/DEX/Backtest)
    - [ ] **Field Rationales Need Overhaul:**
      - ExecutionUrgency, VisibilityPreference too abstract for "executable plan"
      - Redefine as concrete execution specifications
      - Event wiring routes to correct ExecutionWorker type (e.g., TWAPExecutionWorker)
    - [ ] **"Universal → Connector Translation Examples" Table is Obsolete:**
      - Translation happens in IExecutionConnector, not from ExecutionPlan
      - Remove or replace with correct flow description

- [ ] **CausalityChain: Rejection Tracking & Field Cleanup** (2025-12-07)
  - **Source:** `docs/development/backend/dtos/CAUSALITY_DESIGN.md`
  - **Documentation Issues (from DTO_ARCHITECTURE.md review):**
    - [ ] **Needs Rejection Variant:**
      - Current: only tracks SUCCESSFUL decision chains
      - Proposed: support rejection tracking
      - Fields: rejection_reason, rejected_signal_ids, rejected_risk_ids
      - Options: rejection fields in CausalityChain OR separate RejectionChain DTO
    - [ ] **Order/Fill IDs Do NOT Belong in StrategyJournal:**
      - Order/Fill = StrategyLedger domain (WHAT happened)
      - StrategyJournal = decision rationale (WHY)
      - TradePlanID links Journal ↔ Ledger
      - See: TRADE_LIFECYCLE.md for correct separation
      - Update documentation to remove order_ids/fill_ids from Journal

- [ ] **DTO_ARCHITECTURE.md: Overkoepelende Issues** (2025-12-04)
  - **Context:** Issues die niet DTO-specifiek zijn (DTO-specifieke items zijn verdeeld boven)
  - **Source:** User review session 2025-12-04
  
  **Overkoepelende Items:**
  - [ ] **Architectural Pattern Diagram is Incorrect:**
    - Current (wrong) pattern in document:
      ```
      PlanningAggregator
        → ExecutionCommand
          → ExecutionCommandBatch
            → ExecutionGroup
      ```
    - Problems: 
      - PlanningAggregator doesn't exist as separate component
      - ExecutionGroup mentioned too early - it's just an order container
      - ExecutionGroup is created DURING execution, not during planning
    - Action: Update architectural pattern to reflect reality
  - [ ] **Dynamic Exit Logic Needs Deeper Explanation:**
    - What exactly IS dynamic exit logic?
    - Flow implications: PositionMonitor → Signal → StrategyDirective → ExitPlan?
    - How does trailing stop work in this model?
    - Action: Full explanation needed with flow diagram
  - [ ] **Rejected DTO Needed for StrategyPlanner:**
    - When StrategyPlanner rejects signals/risks, this is NOT captured
    - Quant analysis needs: "Why did we NOT trade?"
    - Proposed: `RejectedDirective` or `RejectionEvent` DTO
    - Fields: signal_ids, risk_ids, rejection_reason, rejection_timestamp
    - Consumer: StrategyJournalWriter (for quant analysis)

### Recently Completed

- [x] **ExecutionGroup: REMOVE metadata field** (2025-11-27 → 2025-12-07) ✅
  - **Resolution:** Removed `metadata: dict[str, Any]` - strategy params belong in ExecutionPlan
  - **Scope:** Code + tests (23 tests) + EXECUTION_GROUP_DESIGN.md

- [x] **ExecutionDirective: REMOVE iceberg_preference field** (2025-12-02 → 2025-12-07) ✅
  - **Resolution:** Removed field, updated docstring with note about visibility_preference
  - **Scope:** Code + DTO_ARCHITECTURE.md + STRATEGY_DIRECTIVE_DESIGN.md

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
**Location:** `backend/config/`

**Components:**
- [ ] ConfigLoader (YAML → Pydantic models)
- [ ] ConfigValidator (handler validation, params, circular dependencies)
- [ ] ConfigTranslator (Config → BuildSpecs)

**Deliverable:** YAML → BuildSpecs pipeline working (target: 80+ tests)

---

### Week 3: Factories - Assembly Infrastructure

**Dependencies:** Week 1 + Week 2  
**Location:** `backend/assembly/`

**Factories:**
- [ ] PluginRegistry (plugin discovery & loading)
- [ ] WorkerFactory (worker instantiation from BuildSpecs)
- [ ] EventWiringFactory (EventAdapter assembly from BuildSpecs)
- [ ] StrategyFactory (complete strategy orchestration)
- [ ] WorkerMetadataRegistry (runtime registry for manifest metadata)

**Deliverable:** Complete strategy assembly from BuildSpecs (target: 70+ tests)

---

### Week 4: Platform Components - Event Infrastructure

**Dependencies:** Week 3  
**Location:** `backend/core/`

**Components:**
- [ ] EventAdapter (bus-agnostic worker wrapper)
- [ ] FlowCoordinator (run lifecycle orchestration)
- [ ] PlanningAggregator (4-plan coordinator)
- [ ] StrategyCache Runtime Validation (optional)

**Open Design Issues:**
- [ ] **Issue #5: TradePlan in CausalityChain** - How/when included?
- [ ] **Issue #6: ExecutionCommandBatch execution_mode** - Decision algorithm needed
- [ ] **Issue #7: StrategyDirective Architecture Refactor** - Remaining: `position_size` → `target_position_size`

**Deliverable:** Core platform components (target: 70+ tests)

---

### Week 5: Base Workers - Worker Foundation

**Dependencies:** Week 4  
**Location:** `backend/workers/base/`

- [ ] BaseWorker (abstract foundation)
- [ ] ContextWorker, SignalDetector, RiskMonitor
- [ ] StrategyPlanner, PlanningWorker

**Deliverable:** Worker foundation (target: 40+ tests)

---

### Week 6: Orchestration - Execution Flow

**Dependencies:** Week 5  
**Location:** `backend/orchestration/`

- [ ] StrategyRunner (main execution loop)
- [ ] Error handling & edge cases

**Deliverable:** End-to-end tick processing (target: 30+ tests)

---

### Week 7: Integration & Polish - Production Ready

**Dependencies:** Week 6

- [ ] OperationService (strategy lifecycle)
- [ ] End-to-end integration tests
- [ ] Multi-strategy scenarios
- [ ] Error handling

**Deliverable:** Production-ready platform

---

## 📋 Architectural Decisions & Design Notes

> **Complete design docs:** See `docs/development/` and `docs/architecture/`

### Key Decisions

- **Config Schema Naming:** `*_schema.py` files, class names WITHOUT "DTO" suffix
- **Implementation Order:** Config Schemas → Bootstrap → Factories → Platform → Workers
- **Documentation:** TODO.md for tasks, IMPLEMENTATION_STATUS.md for metrics (SRP)

### Design Documents

**Active:**
- [EVENTADAPTER_DESIGN.md](development/EVENTADAPTER_DESIGN.md)
- [CONFIG_BUILDSPEC_TRANSLATION_DESIGN.md](development/CONFIG_BUILDSPEC_TRANSLATION_DESIGN.md)
- [BASEWORKER_DESIGN_PRELIM.md](development/BASEWORKER_DESIGN_PRELIM.md)
- [FLOW_INITIATOR_DESIGN.md](development/backend/core/FLOW_INITIATOR_DESIGN.md) ✅

**Architecture:**
- [LAYERED_ARCHITECTURE.md](architecture/LAYERED_ARCHITECTURE.md)
- [EVENT_DRIVEN_WIRING.md](architecture/EVENT_DRIVEN_WIRING.md)
- [WORKER_TAXONOMY.md](architecture/WORKER_TAXONOMY.md)

---

## 🎯 Next Actions

**Current:** Week 1 - Configuration Schemas

1. Start branch: `feature/config-schemas-week1`
2. TDD: Write 20+ tests first (RED)
3. Implement WorkerManifest + SchemaReference (GREEN)
4. Quality gates: Pylint 10/10

**See:** [TDD_WORKFLOW.md](coding_standards/TDD_WORKFLOW.md)

---

**Last Updated:** 2025-12-04  
**Archive Policy:** Completed items > 7 days → [TODO_COMPLETED.md](archive/TODO_COMPLETED.md)
