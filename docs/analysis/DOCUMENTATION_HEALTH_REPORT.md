# Documentation Health Report
**Status:** DRAFT
**Date:** 2025-11-20

## 1. Introduction
This report summarizes the findings of the "Comprehensive Documentation Audit" performed to align the `SimpleTraderV3` documentation corpus with the new "Execution Anchor" architecture (`TradePlan`).

## 2. Architectural Audit (Core Docs)

### 2.1. Critical Gaps
The following documents are **structurally inconsistent** with the new architecture:

| Document | Issue | Severity | Recommendation |
| :--- | :--- | :--- | :--- |
| `EXECUTION_FLOW.md` | Describes a flat "Order -> Ledger" flow. Misses `TradePlan` and `ExecutionGroup` hierarchy. | **CRITICAL** | **Rewrite** Sync Flow diagram and text. |
| `PIPELINE_FLOW.md` | Does not mention `TradePlan` creation in Phase 3. | **HIGH** | Update Phase 3 & 4b. |
| `EVENT_ARCHITECTURE.md` | Missing lifecycle events (`TRADE_PLAN_CREATED`). | **MEDIUM** | Add Lifecycle Events section. |

### 2.2. Terminology Scan Results

| Term | Status | Findings | Action |
| :--- | :--- | :--- | :--- |
| `RoutingPlan` | **Deprecated** | Found in `TODO.md` and many `#Archief` files. | Remove from `TODO.md`. Ignore `#Archief`. |
| `Trade Object` | **Clean** | 0 results. | None. |
| `Position Object` | **Clean** | Only in `#Archief`. | None. |
| `StrategyDirective` | **Ambiguous** | Used as "Root" in old docs, but is now just a "Decision". | Clarify role in `PIPELINE_FLOW.md`. |

## 3. Action Plan (Harmonization Roadmap)

### Step 1: Fix Critical Architecture Docs
- [ ] **Rewrite `EXECUTION_FLOW.md`**:
    - Introduce `ExecutionTranslator` creating `ExecutionGroup`.
    - Show `ExecutionHandler` linking orders to `group_id`.
- [ ] **Update `PIPELINE_FLOW.md`**:
    - Phase 3: Explicitly state `StrategyPlanner` creates `TradePlan`.

### Step 2: Cleanup `TODO.md`
- [ ] Remove references to `RoutingPlan` (replaced by `ExecutionIntent`).
- [ ] Remove obsolete "Future" tasks that contradict current design.

### Step 3: Archive Obsolete Docs
- [ ] Move `docs/development/backend/core/FLOW_INITIATOR_DESIGN.md` to `#Archief` (if superseded).
- [ ] Move `docs/development/backend/dtos/CAUSALITY_CHAIN_DESIGN.md` to `#Archief` (if superseded by `DTO_ARCHITECTURE`).

## 4. Conclusion
The codebase has moved to a sophisticated "Plan-centric" model, but the documentation still largely reflects an "Order-centric" model. Closing this gap is essential to prevent developer confusion.
