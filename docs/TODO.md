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
| Technical Debt | 2 | 4 | 🔄 50% (2 open) |

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

- [ ] **ExecutionGroup: Review `metadata` field usage** (2025-11-27)
  - **Issue:** `metadata: dict[str, Any]` is a code smell
  - **Scope:** `backend/dtos/execution/execution_group.py`
  - **Priority:** Medium

- [ ] **DTO_ARCHITECTURE.md: Review Discussion Points** (2025-12-04) 🔴 HIGH
  - **Context:** Full document review revealed 21 architectural inconsistencies
  - **Status:** DISCUSSION REQUIRED before document can be considered DEFINITIVE
  - **Source:** User review session 2025-12-04

### Recently Completed

- [x] **ExecutionDirective: REMOVE iceberg_preference field** (2025-12-02 → 2025-12-07) ✅
  - **Resolution:** Removed field, updated docstring with note about visibility_preference
  - **Scope:** Code + DTO_ARCHITECTURE.md + STRATEGY_DIRECTIVE_DESIGN.md
  
  <details>
  <summary>📋 Discussion Points (21 items - FULL CONTEXT)</summary>
  
  ---
  
  ### 1. ExecutionPlan Output: Concrete Strategy, NOT Trade-offs
  
  **Current (WRONG):** ExecutionPlan describes "universal trade-offs" (urgency, visibility, slippage preferences)
  
  **Proposed (CORRECT):** ExecutionPlan = concrete execution strategy (e.g., TWAP, ICEBERG, SINGLE)
  - ExecutionPlanner decides strategy based on ExecutionDirective + confidence
  - Output should be an **executable plan**, not preferences to interpret
  - Example: `execution_strategy: TWAP` not `execution_urgency: 0.3`
  
  **Action:** Redefine ExecutionPlan as concrete execution specification
  
  ---
  
  ### 2. ExecutionCommand Definition Clarification
  
  **Current:** "Final aggregated execution instruction"
  
  **Proposed:** "Aggregated plans which form a complete execution instruction"
  - Emphasize: aggregation of Entry/Size/Exit/ExecutionPlan into single command
  - Clear that this is the OUTPUT of plan aggregation
  
  **Action:** Update definition in DTO_ARCHITECTURE.md
  
  ---
  
  ### 3. Missing DTOs in Taxonomy Section
  
  **Issue:** DTO Taxonomy section is incomplete
  
  **Missing DTOs:**
  - `Order` - Individual order tracking (exists in code)
  - `Fill` - Exchange execution confirmation (exists in code)
  - `TradePlan` - Execution anchor with TPL_ prefix (exists in code)
  
  **Action:** Add these to DTO Taxonomy section under appropriate categories
  
  ---
  
  ### 4. StrategyDirective "WHY this DTO exists" Section Cleanup
  
  **Issues identified:**
  
  **a. DRY Violation:** First bullet point lists scope field directive types (NEW_TRADE, MODIFY_EXISTING, CLOSE_EXISTING) - this is DUPLICATED in the Scope section below
  - **Action:** Remove from first bullet, keep only in dedicated Scope section
  
  **b. Terminology:** Still says "Routing" in places
  - **Action:** Replace "Routing" → "Execution" throughout
  
  **c. Mutability Discussion Needed:** Document claims StrategyDirective is mutable
  - **Question:** Is this correct? Should StrategyDirective be immutable after creation?
  - **Action:** Architecture discussion needed
  
  ---
  
  ### 5. StrategyDirective Confidence Field Rationale is WRONG
  
  **Current (WRONG):** "Low confidence = skip or reduce size"
  
  **Problem:** Decision to skip is StrategyPlanner's responsibility, NOT individual planners'
  - By the time directive reaches planners, StrategyPlanner ALREADY DECIDED TO ACT
  - If StrategyPlanner wanted to skip, it would NOT emit a directive at all
  
  **Correct Usage:** Individual planners use confidence score to SELECT planner type
  - High confidence → aggressive planner variant
  - Low confidence → conservative planner variant
  - NOT for skip/no-skip decisions
  
  **Action:** Rewrite confidence field rationale
  
  ---
  
  ### 6. Rejected DTO Needed for StrategyPlanner
  
  **Issue:** When StrategyPlanner rejects signals/risks, this is NOT captured anywhere
  
  **Why important:**
  - Quant analysis needs: "Why did we NOT trade?"
  - Rejection reasons must be documented for learning/tuning
  - Silent rejection = lost information
  
  **Proposed Solution:**
  - New DTO: `RejectedDirective` or `RejectionEvent`
  - Fields: signal_ids, risk_ids, rejection_reason, rejection_timestamp
  - Consumer: StrategyJournalWriter (for quant analysis)
  
  **Action:** Design RejectedDirective DTO
  
  ---
  
  ### 7. StrategyDirective Enrichment Violates SRP
  
  **Current (WRONG):** order_ids added to StrategyDirective post-execution
  
  **Problem:**
  - Orders and fills are BUSINESS LOGIC (StrategyLedger domain)
  - StrategyDirective is STRATEGY DECISION (StrategyJournal domain)
  - Mixing these violates Single Responsibility Principle
  
  **See:** TradePlan lifecycle - TradePlan is the anchor, NOT StrategyDirective
  
  **Action:** Remove order_id enrichment from StrategyDirective lifecycle description
  
  ---
  
  ### 8. StrategyDirective Lifecycle "Referenced" is Unclear
  
  **Current:** "Referenced throughout execution pipeline via causality.strategy_directive_id"
  
  **Questions:**
  - When is StrategyDirective's task COMPLETE?
  - What is its PURPOSE after planners have consumed it?
  - Should it be discarded after ExecutionCommand creation?
  
  **Action:** Define strict lifecycle boundaries
  
  ---
  
  ### 9. MODIFY_EXISTING Scope Can Apply to Entry Plans
  
  **Current (INCOMPLETE):** Documentation implies MODIFY_EXISTING only for exit/size modifications
  
  **Reality:** Unfilled entry orders CAN be modified
  - Entry order at limit price not filled → adjust price
  - Entry order partially filled → modify remaining quantity
  
  **Action:** Update Scope Semantics table to include entry plan modifications
  
  ---
  
  ### 10. PlanningAggregator Terminology Still Present
  
  **Issue:** Document still references "PlanningAggregator" as separate component
  
  **Reality:** This aggregation happens in BaseExecutionPlanner boilerplate code
  - No separate PlanningAggregator component exists
  - Aggregation is automatic within ExecutionPlanner
  
  **Action:** Replace PlanningAggregator references with correct implementation location
  
  ---
  
  ### 11. Plan Validation Responsibility Unclear
  
  **Question:** Without PlanningAggregator, who validates plan content?
  
  **Options:**
  - **Option A:** BaseWorker validates (current implicit assumption)
  - **Option B:** ExecutionWorker validates (consumer validates)
  
  **Consideration:** If BaseWorker shouldn't validate plan CONTENT, only structure...
  - Content validation = business logic
  - Structure validation = DTO integrity
  
  **Action:** Decision needed on validation responsibility
  
  ---
  
  ### 12. "Dynamic Exit Logic" Needs Deeper Explanation
  
  **Current:** Brief mention in ExitPlan section
  
  **Questions:**
  - What exactly IS dynamic exit logic?
  - What are the flow implications?
  - Does PositionMonitor → emit Signal → new StrategyDirective → new ExitPlan?
  - How does trailing stop work in this model?
  
  **Action:** Full explanation needed with flow diagram
  
  ---
  
  ### 13. ExecutionPlan "WHY this DTO exists" Point 4 is WRONG
  
  **Current (WRONG):** "Translation layer converts ExecutionPlan → connector-specific execution specs"
  
  **Reality:**
  1. ExecutionPlan is executed by ExecutionWorker
  2. ExecutionWorker handles ALL Ledger interaction
  3. ExecutionWorker creates individual Orders
  4. Orders passed to IExecutionConnector in ExecutionEnvironment
  5. IExecutionConnector does exchange translation (CEX/DEX/Backtest)
  
  **Action:** Rewrite point 4 with correct flow
  
  ---
  
  ### 14. ExecutionPlan Field Rationales Need Overhaul
  
  **Current (WRONG):** Fields like ExecutionUrgency, VisibilityPreference, PreferredExecutionStyle described as "trade-offs to interpret"
  
  **Problem:** These are NOT concrete enough for an "executable plan"
  
  **Correct Model:**
  - ExecutionDirective (input) contains trade-off hints (urgency, etc.)
  - ExecutionPlanner processes these + confidence
  - ExecutionPlan (output) is CONCRETE: specific strategy (TWAP, ICEBERG)
  - Event wiring routes to correct ExecutionWorker type (e.g., TWAPExecutionWorker)
  
  **Action:** Redefine fields as concrete execution specifications
  
  ---
  
  ### 15. "Universal → Connector Translation Examples" Table is Obsolete
  
  **Current:** Table showing how universal trade-offs translate to CEX/DEX/Backtest
  
  **Problem:** This translation model is incorrect (see point 13)
  - Translation happens in IExecutionConnector, not from ExecutionPlan
  - ExecutionPlan should already be concrete
  
  **Action:** Remove or replace with correct flow description
  
  ---
  
  ### 16. Execution DTOs "Architectural Pattern" is Incorrect
  
  **Current pattern shows:**
  ```
  PlanningAggregator
    → ExecutionCommand
      → ExecutionCommandBatch
        → ExecutionGroup
  ```
  
  **Problems:**
  - PlanningAggregator doesn't exist as separate component
  - ExecutionGroup mentioned too early - it's just an order container
  - ExecutionGroup is created DURING execution, not during planning
  
  **Action:** Update architectural pattern to reflect reality
  
  ---
  
  ### 17. ExecutionCommandBatch Extra Fields - Where Do They Come From?
  
  **Fields in question:**
  - `execution_mode` (SEQUENTIAL/PARALLEL/ATOMIC)
  - `rollback_on_failure`
  - `timeout_seconds`
  
  **Question:** Where do these originate?
  
  **Hypothesis:** StrategyPlanner → StrategyDirective → Batch
  - If so: These fields should be in StrategyDirective
  - Currently NOT in StrategyDirective
  
  **Alternative:** Derived from other signals?
  
  **Action:** Trace field origins, update StrategyDirective if needed
  
  ---
  
  ### 18. Execution Strategy Types Table - DCA is WRONG
  
  **Current:** DCA listed in ExecutionGroup "Execution Strategy Types" table
  
  **Problem:** DCA is a PLANNING strategy, not an execution strategy
  - DCA = Dollar-Cost Averaging = systematic position building over time
  - This is StrategyPlanner/SizePlanner domain
  - NOT ExecutionWorker domain
  
  **Note:** Already fixed in code (commit `3b45af6`) but document still wrong
  
  **Action:** Remove DCA from Execution Strategy Types table
  
  ---
  
  ### 19. CausalityChain Needs Rejection Variant
  
  **Current:** CausalityChain only tracks SUCCESSFUL decision chains
  
  **Problem:** No way to track WHY we did NOT trade
  
  **Proposed:**
  - CausalityChain should support rejection tracking
  - Fields: rejection_reason, rejected_signal_ids, rejected_risk_ids
  - Or: Separate RejectionChain DTO?
  
  **Action:** Decision needed on rejection tracking structure
  
  ---
  
  ### 20. Order/Fill IDs Do NOT Belong in StrategyJournal
  
  **Current (WRONG):** "order_ids, fill_ids → StrategyJournal"
  
  **Problem:**
  - Order/Fill data is BUSINESS LOGIC
  - Belongs in StrategyLedger, NOT StrategyJournal
  - StrategyJournal = decision rationale (WHY)
  - StrategyLedger = execution state (WHAT happened)
  
  **Cross-query anchor:** TradePlanID links Journal ↔ Ledger
  - See: TRADE_LIFECYCLE.md for correct separation
  
  **Action:** Update CausalityChain documentation to remove order_ids/fill_ids from Journal
  
  ---
  
  ### 21. TradePlan, Order, Fill DTOs Missing from Document
  
  **Issue:** These DTOs exist in code but are NOT documented in DTO_ARCHITECTURE.md
  
  **Missing documentation:**
  - **TradePlan** - Execution anchor (TPL_ prefix), ACTIVE/CLOSED status
  - **Order** - Individual order tracking (OrderType, OrderStatus, OrderSide)
  - **Fill** - Exchange execution confirmation
  
  **Location in code:**
  - `backend/dtos/state/trade_plan.py`
  - `backend/dtos/state/order.py`
  - `backend/dtos/state/fill.py`
  
  **Action:** Add full documentation sections for these State DTOs
  
  ---
  
  </details>
  
  **Next Steps:**
  1. Schedule architecture discussion session
  2. Work through items 1-21 systematically
  3. Update DTO_ARCHITECTURE.md after decisions
  4. Update code where architectural changes needed

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
