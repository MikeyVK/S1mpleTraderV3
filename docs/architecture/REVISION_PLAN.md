# Documentation Revision Plan: SRP & Container-Based Architecture

**Goal:** Refine `TRADE_LIFECYCLE.md`, `PIPELINE_FLOW.md`, and `EXECUTION_FLOW.md` to strictly adhere to SRP, defining `TradePlan`, `ExecutionGroup`, and `Order` as data containers owned by `StrategyLedger`, with Workers acting solely as stateless logic units ("Users").

## 1. Core Architectural Concepts (The "North Star")

To ensure consistency, we define these non-negotiable principles:

1.  **The Ledger is the Bank:** `StrategyLedger` is the *only* component that owns, creates, and updates the lifecycle state of `TradePlan`, `ExecutionGroup`, and `Order`.
2.  **Workers are Account Holders:** Workers (`StrategyPlanner`, `ExecutionWorker`) contain *logic*. They do not "own" the data. They *request* transactions (create plan, update order) from the Ledger.
3.  **Containers vs. Logic:**
    *   **Container:** `TradePlan` (Strategic Intent), `ExecutionGroup` (Tactical Progress), `Order` (Atomic Action).
    *   **Logic:** `StrategyPlanner` (Decides Strategy), `ExecutionPlanner` (Decides Tactics), `ExecutionWorker` (Executes Action).
4.  **Standardized Terminology:**
    *   **ExecutionWorker:** The plugin component containing specific execution logic (e.g., TWAPWorker, IcebergWorker).
    *   **IExecutionConnector:** The interface injected into ExecutionWorkers to interact with the environment (Live/Paper/Backtest).
    *   **ExecutionPlanner:** The specific planner that decides *which* ExecutionWorker to use and configures it.

---

## 2. Revision Strategy per Document

### A. `TRADE_LIFECYCLE.md` (The Data & Ownership Model)

**Current Issues:**
*   Ownership Matrix conflates "Logical Owner" (Decider) with "Technical Creator" (Ledger).
*   "Chicken-and-Egg" confusion regarding who creates `ExecutionGroup`.

**Proposed Changes:**
1.  **Rename "Ownership Matrix" to "Responsibility Matrix":**
    *   **Columns:** `Entity`, `Logical Owner (Decider)`, `State Owner (Ledger)`, `Operator (Worker)`.
    *   **Example:** `TradePlan` | Decider: `StrategyPlanner` | Owner: `StrategyLedger` | Operator: `StrategyPlanner`.
2.  **Define "Container Hierarchy" (Section 1):**
    *   Explicitly state that these are *Ledger Entities*.
    *   Diagram: `StrategyLedger` wrapping all three entities.
3.  **Clarify Creation Flow (Section 2):**
    *   Describe the "Request-Response" pattern.
    *   *Example:* `ExecutionPlanner` emits `ExecutionDirective` -> Platform/Ledger creates `ExecutionGroup` -> `ExecutionWorker` receives ID.

### B. `PIPELINE_FLOW.md` (The Logic Flow)

**Current Issues:**
*   Phase 5/6 descriptions might still reference deprecated `ExecutionHandler` or old patterns.
*   Needs to explicitly link `ExecutionIntent` to the *creation* of `ExecutionGroup` in the Ledger.

**Proposed Changes:**
1.  **Update Phase 5 (Execution Planning):**
    *   Clarify that `ExecutionPlanner` outputs `ExecutionDirective` (containing concrete `ExecutionPlan`).
    *   **Direct Wiring:** The `ExecutionDirective` is routed directly to the specific `ExecutionWorker` (e.g., `TWAPWorker`) via EventBus wiring.
2.  **Update Phase 6 (Execution):**
    *   **Creation:** The `ExecutionWorker` receives the directive and **initializes** the `ExecutionGroup` in the `StrategyLedger`.
    *   **State Access:** The Worker queries `ExecutionGroup` state from the `StrategyLedger` (via injected `IStrategyLedger` capability).
    *   **Execution:** The Worker executes logic using the injected `IExecutionConnector`.
3.  **Refine "ExecutionIntent" Section:**
    *   **Remove** `ExecutionTranslator` and `ExecutionIntent` concepts entirely.
    *   **Rationale:** Avoid abstracting away "quant magic". Planners should explicitly configure specific execution algorithms.
    *   Describe how `ExecutionPlanner` maps strategy directly to specific Worker configurations.

### C. `EXECUTION_FLOW.md` (The Technical Sequence)

**Current Issues:**
*   Diagrams show `ExecutionHandler` "creating" OrderIDs and "recording" them.
*   Needs to emphasize the *Ledger* as the authority.

**Proposed Changes:**
1.  **Replace `ExecutionHandler` with `ExecutionWorker`:**
    *   Standardize on `ExecutionWorker` as the active component.
2.  **Update Sequence Diagrams:**
    *   **Sync Flow:** `ExecutionWorker` (via injected Connector) -> `StrategyLedger.create_order()` -> `Order` (Created) -> `Connector.place_order()`.
    *   **Async Flow:** `Connector` (Fill) -> `ExecutionWorker` -> `StrategyLedger.update_order()` -> `Fill` (Recorded).
3.  **Remove "Causality vs Reality" ambiguity:**
    *   Reaffirm: Ledger = Reality (What happened). Journal = Causality (Why it happened).

---

## 3. Implementation Steps

1.  **Step 1:** Update `TRADE_LIFECYCLE.md` to establish the new "Responsibility Matrix" and Container definitions.
2.  **Step 2:** Update `PIPELINE_FLOW.md` to align Phase 5/6 with the Ledger-centric model.
3.  **Step 3:** Update `EXECUTION_FLOW.md` diagrams and text to reflect `ExecutionWorker` + `StrategyLedger` interaction.
4.  **Step 4:** (Optional) Update `WORKER_TAXONOMY.md` to formally reinstate `ExecutionWorker` and deprecate `ExecutionHandler` if confirmed.

## 4. Verification

*   **Review:** User to review this plan.
*   **Consistency Check:** Ensure all 3 documents tell the same story about who creates an Order and where it lives.
