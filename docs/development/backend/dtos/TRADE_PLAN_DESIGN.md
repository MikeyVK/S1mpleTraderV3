# TradePlan DTO Design

**Status:** Draft
**Layer:** Strategy (Strategic State Container)
**Related Architecture:** 
- [TRADE_LIFECYCLE.md](../../../../architecture/TRADE_LIFECYCLE.md)
- [STRATEGY_LEDGER_DESIGN.md](../../ledger/STRATEGY_LEDGER_DESIGN.md)

## 1. Overview

The `TradePlan` DTO serves as the **Execution Anchor** for a strategy's lifecycle. It provides a stable identity (`plan_id`) that links the Strategy's intent (Journal) with the Market's reality (Ledger).

### 1.1 Architectural Fit
*   **Execution Anchor:** It groups tactical `ExecutionGroups` under one strategic ID.
*   **Cross-Query Key:** It allows Quant tools to join Ledger data (Reality) with Journal data (Context/History).
*   **Minimalist:** It contains *only* the essential fields to define its existence and lifecycle status. Strategic state (e.g., "Grid Level") is stored in the **StrategyJournal**, not here.

## 2. Data Structure

### 2.1 Class: `TradeStatus` (Enum)

Lifecycle state of the plan.

| Value | Description |
| :--- | :--- |
| `ACTIVE` | The plan is live. |
| `CLOSED` | The plan is terminated. |

### 2.2 Class: `TradePlan` (DTO)

**Mutability:** Mutable (`frozen=False`). Only `status` changes.

| Field | Type | Required | Description | Validation |
| :--- | :--- | :--- | :--- | :--- |
| `plan_id` | `str` | Yes | Unique identifier. The anchor for cross-referencing. | Must match `^TPL_\d{8}_\d{6}_[0-9a-z]{5,8}$` |
| `strategy_instance_id` | `str` | Yes | ID of the owning strategy instance. | Non-empty string. |
| `status` | `TradeStatus` | Yes | Current lifecycle state. | Valid Enum value. |
| `created_at` | `datetime` | Yes | Creation timestamp (UTC). Required for Ledger housekeeping (sorting/pruning). | Timezone aware (UTC). |

## 3. Implementation Details

### 3.1 Pydantic Configuration
```python
model_config = {
    "frozen": False,
    "str_strip_whitespace": True,
    "validate_assignment": True
}
```

### 3.2 Validators
1.  **`validate_plan_id_format`**: Ensures `plan_id` starts with `TPL_` and follows the standard timestamp+hash format.

## 4. Usage Example

```python
plan = TradePlan(
    plan_id="TPL_20251030_120000_abc12",
    strategy_instance_id="STRAT_GRID_BTC_01",
    status=TradeStatus.ACTIVE,
    created_at=datetime.now(UTC)
)

# State transition (e.g. Strategy decides to close)
plan.status = TradeStatus.CLOSED
# ledger.update_plan(plan)
```
