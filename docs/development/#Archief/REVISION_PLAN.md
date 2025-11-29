# Documentation Revision Plan: SRP & Container-Based Architecture

**Status:** ✅ Phase 1 Complete (4/4 documents revised)  
**Last Updated:** 2025-11-28  
**Goal:** Revise 4 architecture documents to align with SRP, Container-Based Architecture, and the finalized ExecutionWorker design.

---

## Execution Progress

| Document | Status | Commit | Notes |
|----------|--------|--------|-------|
| `TRADE_LIFECYCLE.md` | ✅ Complete | `6588acb` | v2.0 - Container hierarchy, Ledger access patterns |
| `WORKER_TAXONOMY.md` | ✅ Complete | `d1f9aa5` | v2.0 - 6 worker categories, ExecutionWorker reinstated |
| `EXECUTION_FLOW.md` | ✅ Complete | `9943edd` | v2.0 - ExecutionHandler→ExecutionWorker, diagrams updated |
| `PIPELINE_FLOW.md` | ✅ Complete | pending | v3.0 - Complete rewrite: 1778→481 lines, Signal/Risk terminology, ARCHITECTURE_TEMPLATE |

**Branch:** `docs/architecture-revision`  
**PR Ready:** Yes (all 4 documents complete)

---

## 1. Core Architectural Concepts (The "North Star")

These non-negotiable principles guide all revisions:

1.  **The Ledger is the Bank:** `StrategyLedger` is the *only* component that owns, creates, and updates the lifecycle state of `TradePlan`, `ExecutionGroup`, `Order`, and `Fill`.
2.  **Workers are Account Holders:** Workers contain *logic*. They do not "own" data. They *request* transactions from the Ledger.
3.  **Planners decide WHAT, Workers execute HOW:**
    *   **Planner:** Determines trade intent (what we want to achieve)
    *   **Worker:** Executes trade actions (how to achieve it, including operational lookups)
4.  **On-Demand Container Creation:** Containers are created lazily:
    *   Order creation triggers ExecutionGroup creation (if needed)
    *   ExecutionGroup creation triggers TradePlan creation (if needed)
5.  **Standardized Terminology:**
    *   **ExecutionWorker:** Plugin component with execution logic (e.g., TWAPWorker)
    *   **ExecutionPlanner:** 4th TradePlanner, aggregates 3 plans + chooses algorithm
    *   **IExecutionConnector:** Interface for environment interaction (Live/Paper/Backtest)
    *   **DEPRECATED:** ExecutionHandler, ExecutionService, ExecutionTranslator, ExecutionIntent

---

## 2. SRP: Planner vs Worker Responsibilities

### Planner Responsibility (WHAT)

| TradePlanner | Decision | Ledger Access |
|--------------|----------|---------------|
| EntryPlanner | "Limit order @ $95k" | Reads plan direction (long/short) for close scenarios |
| SizePlanner | "Target size: 1.5 BTC" | Reads current position size for delta calculation |
| ExitPlanner | "SL @ $90k, TP @ $105k" | Reads current exit levels for comparison |
| ExecutionPlanner | "Use TWAP, 12 slices, 60 min" | Reads plan metadata for algo selection |

### Worker Responsibility (HOW)

| ExecutionWorker Task | Description |
|---------------------|-------------|
| Lookup existing orders | "Which SL orders exist for this plan?" |
| Register new containers | Create ExecutionGroup, register Orders |
| Execute via Connector | Place/modify/cancel orders |
| Update state | Record fills, update group progress |

**Key Insight:** The lookup for existing orders belongs to ExecutionWorker (HOW), not ExecutionPlanner (WHAT).

---

## 3. Ledger Access Patterns (Descriptive, No Method Names)

| Component | Ledger Interaction (descriptive) |
|-----------|----------------------------------|
| **StrategyPlanner** | Reads active plans and their status to make strategic decisions |
| **EntryPlanner** | Reads plan direction (long/short) when handling close scenarios |
| **SizePlanner** | Reads current position size to calculate required delta |
| **ExitPlanner** | Reads current exit levels to determine if modification is needed |
| **ExecutionPlanner** | Reads plan metadata to select appropriate execution algorithm |
| **ExecutionWorker** | Full read/write access: creates containers, registers orders, records fills, queries existing orders for modifications |

### Scope-Specific Access

| Scope | StrategyPlanner | Entry | Size | Exit | Execution |
|-------|-----------------|-------|------|------|-----------|
| **NEW_TRADE** | Read: check duplicates | — | — | — | — |
| **MODIFY_EXISTING** | Read: plan status | Read: direction | Read: current_size | Read: exit levels | Read: active groups |
| **CLOSE_EXISTING** | Read: all active plans | Read: direction | Read: full size | Read: all orders | Read: all groups |

---

## 4. Revision Instructions per Document

### A. `TRADE_LIFECYCLE.md` - Foundation Document

**Order:** Revise FIRST (establishes terminology for other docs)

**Changes:**

1. **Remove "Ownership Matrix"** (Section 1.2)
   - The container hierarchy is already clear from the mermaid diagram
   - No replacement matrix needed

2. **Add "Ledger Access Patterns" section**
   - Use descriptive language (no method names)
   - Include the scope-specific access table above

3. **Clarify On-Demand Creation**
   - Containers created lazily when needed
   - Order → ExecutionGroup → TradePlan (bottom-up trigger)

4. **Update Section 6 (ExecutionWorker)**
   - Remove any ExecutionHandler references
   - Emphasize: Worker does operational lookups (HOW), not Planner

5. **Remove ExecutionService references**
   - This component is deprecated (unnecessary complexity)

### B. `WORKER_TAXONOMY.md` - Worker Definitions

**Order:** Revise SECOND (defines ExecutionWorker before pipeline uses it)

**Changes:**

1. **Reinstate ExecutionWorker as 6th Worker Category**
   - Remove "Historical Note: Removed Categories" section
   - Add full ExecutionWorker section with:
     - Purpose: Execute trade actions via Connector
     - Responsibilities: Order placement, modification, cancellation
     - Ledger Access: Full read/write
     - Output: Order state updates

2. **Clarify ExecutionPlanner position**
   - ExecutionPlanner = 4th TradePlanner (not a separate category)
   - Aggregates 3 plans + StrategyDirective
   - Decides WHICH algorithm, not HOW to execute

3. **Add Ledger Access Requirements per Worker Type**
   - Descriptive (no method names)
   - Reference the access patterns from Section 3 above

4. **Update PlanningWorker section**
   - Clarify 4 subtypes: Entry, Size, Exit, Execution
   - ExecutionPlanner aggregates and selects algorithm

### C. `PIPELINE_FLOW.md` - Complete Rewrite

**Order:** Revise THIRD (uses terminology from A and B)

**CRITICAL: This is a COMPLETE REWRITE, not incremental update.**

**Changes:**

1. **Remove entirely:**
   - ExecutionTranslator concept
   - ExecutionIntent abstraction
   - ExecutionService references
   - ExecutionHandler terminology

2. **SWOT Terminology Cleanup** (align with commit `73bc71f`):
   - Opportunity → Signal
   - OpportunityWorker → SignalDetector
   - OpportunitySignal → Signal
   - OPPORTUNITY_DETECTED → SIGNAL_DETECTED
   - opportunity_workers → signal_detectors
   - Threat → Risk
   - ThreatWorker → RiskMonitor
   - ThreatSignal → Risk
   - THREAT_DETECTED → RISK_DETECTED
   - threat_workers → risk_monitors
   - SWOT Quadranten → Signal/Risk Analysis
   - SWOT Confrontatie → Signal/Risk Confrontation

3. **Update Phase 4 (Trade Planning):**
   - 4 TradePlanners: Entry, Size, Exit, Execution
   - ExecutionPlanner aggregates 3 plans + chooses algorithm
   - Output: ExecutionDirective with concrete algorithm config

4. **Update Phase 5 (Execution):**
   - ExecutionWorker receives ExecutionDirective via EventBus wiring
   - Worker does operational lookups (existing orders, groups)
   - Worker interacts with Ledger for state management
   - Worker uses Connector for exchange interaction

5. **Keep language English**
   - Convert any remaining Dutch sections to English

6. **Simplify diagrams**
   - Remove Translator/Intent layers
   - Show: Planners → ExecutionDirective → ExecutionWorker → Ledger/Connector
   - Update all Mermaid diagrams with Signal/Risk terminology

### D. `EXECUTION_FLOW.md` - Diagram Updates

**Order:** Revise FOURTH (final consistency check)

**Changes:**

1. **Replace ExecutionHandler with ExecutionWorker**
   - All diagrams and text
   - Consistent terminology

2. **Update Sequence Diagrams:**
   - Sync Flow: ExecutionWorker → Ledger (register) → Connector (place)
   - Async Flow: Connector (fill) → ExecutionWorker → Ledger (record)

3. **Emphasize Ledger as State Owner**
   - All containers live in Ledger
   - Worker queries Ledger for existing orders during modifications

4. **Remove ExecutionService references**
   - Deprecated concept

---

## 5. Source Materials

Reference these documents during revision:

| Document | Location | Use For |
|----------|----------|---------|
| Trailing Stop Scenario | `docs/development/design_validations/SCENARIO_TRAILING_STOP.md` | MODIFY_EXISTING flow example |
| Modification Flows | `docs/development/design_validations/SCENARIO_MODIFICATION_FLOWS.md` | Scale In/Out, Emergency Exit |
| Long/Short Validation | `docs/development/design_validations/LONG_SHORT_TARGET_SIZE_VALIDATION.md` | target_position_size semantics |
| Concrete TWAP Scenario | `docs/archive/execution_refactor_v4/CONCRETE_EXECUTION_SCENARIO.md` | Integrated protection pattern |
| Pipeline Refinement | `docs/archive/execution_refactor_v4/EXECUTION_PIPELINE_REFINEMENT.md` | EventAdapter wiring pattern |

---

## 6. Verification Checklist

After all revisions, verify:

- [ ] No mentions of `ExecutionHandler` (replaced by ExecutionWorker)
- [ ] No mentions of `ExecutionService` (deprecated)
- [ ] No mentions of `ExecutionTranslator` (removed)
- [ ] No mentions of `ExecutionIntent` abstraction (removed)
- [ ] No mentions of SWOT terminology: Opportunity, Threat, OpportunityWorker, ThreatWorker
- [ ] Signal/Risk terminology used consistently throughout
- [ ] ExecutionWorker is defined as 6th worker category
- [ ] ExecutionPlanner is defined as 4th TradePlanner
- [ ] Ledger access is described, not specified with method names
- [ ] All 4 documents tell consistent story about container ownership
- [ ] All documentation is in English

---

## 7. Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2025-11-15 | Initial revision plan |
| v2.0 | 2025-11-27 | Complete rewrite based on SRP/Planner-Worker analysis, added detailed instructions per document, source materials, verification checklist |
