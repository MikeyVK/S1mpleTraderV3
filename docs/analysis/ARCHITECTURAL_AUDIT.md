# Architectural Audit Report
**Status:** DRAFT
**Date:** 2025-11-20

## 1. Executive Summary
This audit compares the core architectural documentation against the newly adopted `TRADE_LIFECYCLE.md` (The "Definitive" standard).
**Key Finding:** The core flow documents (`PIPELINE_FLOW.md`, `EXECUTION_FLOW.md`) are **out of sync** with the "Execution Anchor" architecture. They describe a direct "Order-centric" flow, whereas the new standard mandates a "Plan-centric" hierarchy (`TradePlan` -> `ExecutionGroup` -> `Order`).

## 2. Gap Analysis: Core Architecture

### 2.1. PIPELINE_FLOW.md vs. TRADE_LIFECYCLE.md
| Feature | PIPELINE_FLOW.md (Current) | TRADE_LIFECYCLE.md (Target) | Severity |
| :--- | :--- | :--- | :--- |
| **Root Entity** | `StrategyDirective` seems to be the main artifact. | `TradePlan` is the root "Execution Anchor". | **HIGH** |
| **Execution Unit** | Mentions `ExecutionDirective` and `ExecutionIntent`. | Explicitly defines `ExecutionGroup` as the tactical unit. | **MEDIUM** |
| **Creation Point** | `StrategyPlanner` produces `StrategyDirective`. | `StrategyPlanner` produces `StrategyDirective` AND creates `TradePlan`. | **HIGH** |

**Action Items:**
- Update Phase 3 (Strategy Planning) to explicitly mention `TradePlan` creation.
- Update Phase 4b (Aggregation) to show how plans link back to `TradePlan.plan_id`.

### 2.2. EXECUTION_FLOW.md vs. TRADE_LIFECYCLE.md
| Feature | EXECUTION_FLOW.md (Current) | TRADE_LIFECYCLE.md (Target) | Severity |
| :--- | :--- | :--- | :--- |
| **Ledger Interaction** | `ExecutionHandler` -> `record_order(order_id)`. | `ExecutionHandler` -> `register_order` (linked to `ExecutionGroup`). | **CRITICAL** |
| **Hierarchy** | Flat: Order -> Ledger. | Nested: TradePlan -> ExecutionGroup -> Order. | **CRITICAL** |
| **IDs** | Only mentions `OrderID` and `FillID`. | Missing `PlanID` and `GroupID` propagation. | **HIGH** |

**Action Items:**
- Rewrite "Sync Flow" diagram to include `ExecutionGroup` creation by `ExecutionTranslator`.
- Update `ExecutionHandler` steps to reference `group_id`.

### 2.3. EVENT_ARCHITECTURE.md
| Feature | Status | Notes |
| :--- | :--- | :--- |
| **Event Vocabulary** | Mostly aligned. | Missing events for Lifecycle state changes? |
| **Missing Events** | `TRADE_PLAN_CREATED`, `EXECUTION_GROUP_CREATED`? | Need to decide if these are *Events* (bus) or just *Ledger Updates* (disk). `TRADE_LIFECYCLE.md` implies Ledger is the source of truth, but UI might need events. |

## 3. Terminology Scan (Preliminary)
*To be populated by Grep Analysis*

## 4. Recommendations
1.  **Prioritize `EXECUTION_FLOW.md` update:** It is factually incorrect regarding the new Ledger hierarchy.
2.  **Update `PIPELINE_FLOW.md`:** To reflect the "Container" concept of `TradePlan`.
