# ExecutionGroup DTO - Conceptueel Ontwerp (STAP 0)

**Status:** Architectural Contract  
**Versie:** 1.0  
**Datum:** 2025-10-28  
**Owner:** Platform Architecture Team

---

## Executive Summary

**ExecutionGroup** is het tracking DTO voor gerelateerde orders die samen een executie-strategie vormen (bijv. TWAP, ICEBERG, DCA). Het biedt **causal traceability** tussen parent directive en child orders, en ondersteunt **atomic group operations** (cancel all, modify all).

**Kernprincipe:**
> ExecutionGroup is de "family tree" van orders - track parent-child relationships en group lifecycle.

---

## 1. Architectural Contract

### 1.1 Responsibility (SRP)

**ExecutionGroup heeft ÉÉN verantwoordelijkheid:**
> "Track order relationships and group lifecycle for multi-order execution strategies"

**NIET verantwoordelijk voor:**
- ❌ Order creation (dat is ExecutionHandler's domein)
- ❌ TWAP/VWAP algoritme (dat is ExecutionTranslator's domein)
- ❌ Fill aggregation (dat is PositionTracker's domein)
- ❌ PnL calculation (dat is PortfolioMonitor's domein)

### 1.2 Core Use Cases

1. **TWAP Order Groups**: Track 10 child orders from 1 parent TWAP directive
2. **Iceberg Order Groups**: Track visible/hidden order pairs per iceberg strategy
3. **DCA Order Groups**: Track recurring buy orders from scheduled DCA directive
4. **Emergency Cancels**: Cancel entire group atomically when risk threshold breached
5. **Partial Fill Tracking**: Monitor group fill ratio vs execution intent target

### 1.3 Field Specification

| **Field** | **Type** | **Required** | **Description** | **Example** |
|-----------|----------|--------------|-----------------|-------------|
| `group_id` | `str` | ✅ Yes | Unique group ID (pattern: `EXG_YYYYMMDD_HHMMSS_xxxxx`) | `"EXG_20251028_143022_a8f3c"` |
| `parent_directive_id` | `str` | ✅ Yes | ExecutionDirective that created this group | `"EXE_20251028_143020_b7c4d"` |
| `execution_strategy` | `ExecutionStrategyType` | ✅ Yes | Strategy type (SINGLE, TWAP, ICEBERG, DCA) | `ExecutionStrategyType.TWAP` |
| `order_ids` | `list[str]` | ✅ Yes | List of connector order IDs (empty initially) | `["order_123", "order_124"]` |
| `status` | `GroupStatus` | ✅ Yes | Group lifecycle status | `GroupStatus.ACTIVE` |
| `created_at` | `datetime` | ✅ Yes | Group creation timestamp (UTC) | `2025-10-28T14:30:22Z` |
| `updated_at` | `datetime` | ✅ Yes | Last update timestamp (UTC) | `2025-10-28T14:35:15Z` |
| `target_quantity` | `Optional[Decimal]` | ❌ No | Target quantity for group (if applicable) | `Decimal("100.0")` |
| `filled_quantity` | `Optional[Decimal]` | ❌ No | Actual filled quantity across all orders | `Decimal("87.5")` |
| `cancelled_at` | `Optional[datetime]` | ❌ No | Cancellation timestamp (if cancelled) | `2025-10-28T14:40:00Z` |
| `completed_at` | `Optional[datetime]` | ❌ No | Completion timestamp (if completed) | `2025-10-28T15:00:00Z` |
| `metadata` | `Optional[dict]` | ❌ No | Strategy-specific metadata (JSON) | `{"chunk_size": 10, "interval_seconds": 300}` |

### 1.4 Enums

#### ExecutionStrategyType
```python
class ExecutionStrategyType(str, Enum):
    """Execution strategy types."""
    SINGLE = "SINGLE"          # Single order (no grouping needed)
    TWAP = "TWAP"              # Time-Weighted Average Price
    VWAP = "VWAP"              # Volume-Weighted Average Price
    ICEBERG = "ICEBERG"        # Iceberg order (visible/hidden pairs)
    DCA = "DCA"                # Dollar-Cost Averaging
    LAYERED = "LAYERED"        # Layered limit orders
    POV = "POV"                # Percentage of Volume
```

#### GroupStatus
```python
class GroupStatus(str, Enum):
    """Group lifecycle status."""
    PENDING = "PENDING"        # Created, no orders yet
    ACTIVE = "ACTIVE"          # Orders being executed
    COMPLETED = "COMPLETED"    # All orders filled/complete
    CANCELLED = "CANCELLED"    # Group cancelled (all orders cancelled)
    FAILED = "FAILED"          # Execution failed (error state)
    PARTIAL = "PARTIAL"        # Some orders filled, group stopped
```

---

## 2. Field-by-Field Specification

### 2.1 group_id (str)

**Purpose:** Unique identifier for execution group  
**Format:** `EXG_YYYYMMDD_HHMMSS_xxxxx` (military datetime + 5 char hash)  
**Generated:** Via `generate_execution_group_id()` in `id_generators.py`  
**Validation:** Regex pattern `^EXG_\d{8}_\d{6}_[0-9a-z]{5}$`

**Example:**
```python
group_id="EXG_20251028_143022_a8f3c"
```

### 2.2 parent_directive_id (str)

**Purpose:** Link to ExecutionDirective that spawned this group  
**Format:** `EXE_YYYYMMDD_HHMMSS_xxxxxxxx` (standard ExecutionDirective ID)  
**Validation:** Must match existing ExecutionDirective ID  
**Causal Chain:** `StrategyDirective → ExecutionDirective → ExecutionGroup → Order`

**Example:**
```python
parent_directive_id="EXE_20251028_143020_b7c4d890"
```

### 2.3 execution_strategy (ExecutionStrategyType)

**Purpose:** Classify group type for strategy-specific handling  
**Values:** SINGLE, TWAP, VWAP, ICEBERG, DCA, LAYERED, POV  
**Rationale:** Different strategies require different group management logic

**Translation Matrix:**

| **ExecutionIntent Hint** | **Translator Chooses** | **ExecutionGroup Strategy** |
|--------------------------|------------------------|------------------------------|
| `preferred_execution_style="TWAP"` | TWAPExecutionTranslator | `ExecutionStrategyType.TWAP` |
| `visibility_preference=0.1` | IcebergTranslator | `ExecutionStrategyType.ICEBERG` |
| `chunk_distribution="UNIFORM"` | LayeredTranslator | `ExecutionStrategyType.LAYERED` |
| (none) + urgency=0.9 | MarketTranslator | `ExecutionStrategyType.SINGLE` |

**Example:**
```python
execution_strategy=ExecutionStrategyType.TWAP
```

### 2.4 order_ids (list[str])

**Purpose:** Track all connector order IDs belonging to this group  
**Initial State:** Empty list `[]` at group creation  
**Updated:** By ExecutionHandler as orders are placed  
**Validation:** Each ID must be unique within group

**Example:**
```python
# Initial state
order_ids=[]

# After TWAP places 5 orders
order_ids=["binance_order_123", "binance_order_124", "binance_order_125", 
           "binance_order_126", "binance_order_127"]
```

### 2.5 status (GroupStatus)

**Purpose:** Track group lifecycle state machine  
**Initial:** `GroupStatus.PENDING` at creation  
**State Transitions:**

```
PENDING → ACTIVE     (first order placed)
ACTIVE → COMPLETED   (all orders filled)
ACTIVE → CANCELLED   (group cancellation requested)
ACTIVE → FAILED      (execution error occurred)
ACTIVE → PARTIAL     (some fills, group stopped early)
```

**Example:**
```python
status=GroupStatus.ACTIVE
```

### 2.6 created_at / updated_at (datetime)

**Purpose:** Audit trail timestamps  
**Timezone:** UTC only (via `datetime.now(timezone.utc)`)  
**Created:** Set once at group creation  
**Updated:** Modified on every status change or order_ids append

**Example:**
```python
created_at=datetime(2025, 10, 28, 14, 30, 22, tzinfo=timezone.utc)
updated_at=datetime(2025, 10, 28, 14, 35, 15, tzinfo=timezone.utc)
```

### 2.7 target_quantity / filled_quantity (Optional[Decimal])

**Purpose:** Track fill progress for quantity-based groups  
**Applicable:** TWAP, DCA, LAYERED (quantity-driven strategies)  
**Not Applicable:** ICEBERG (visibility-driven), SINGLE (atomic)  
**Precision:** `max_digits=20, decimal_places=8`

**Derived Metrics:**
```python
fill_ratio = filled_quantity / target_quantity  # 0.0 - 1.0
remaining_quantity = target_quantity - filled_quantity
```

**Example:**
```python
target_quantity=Decimal("100.0")     # TWAP target: 100 BTC
filled_quantity=Decimal("87.5")      # 87.5 BTC filled so far
# Fill ratio: 87.5%
```

### 2.8 cancelled_at / completed_at (Optional[datetime])

**Purpose:** Final state timestamps  
**Cancelled:** Set when status → CANCELLED  
**Completed:** Set when status → COMPLETED  
**Validation:** Cannot have both set (XOR constraint)

**Example:**
```python
# Successful completion
completed_at=datetime(2025, 10, 28, 15, 0, 0, tzinfo=timezone.utc)
cancelled_at=None

# Emergency cancel
completed_at=None
cancelled_at=datetime(2025, 10, 28, 14, 40, 0, tzinfo=timezone.utc)
```

### 2.9 metadata (Optional[dict])

**Purpose:** Strategy-specific configuration storage  
**Format:** JSON-serializable dict  
**Use Cases:**
- TWAP: `{"chunk_size": 10, "interval_seconds": 300, "start_time": "..."}`
- ICEBERG: `{"visible_ratio": 0.2, "refresh_threshold": 0.5}`
- DCA: `{"frequency": "daily", "amount_usd": 100}`

**Validation:** None (free-form JSON)

**Example:**
```python
metadata={
    "chunk_size": 10,
    "interval_seconds": 300,
    "total_chunks": 10,
    "chunks_placed": 5
}
```

---

## 3. Validation Rules

### 3.1 Field-Level Validation

| **Field** | **Validation Rule** | **Error Message** |
|-----------|-------------------|-------------------|
| `group_id` | Regex `^EXG_\d{8}_\d{6}_[0-9a-z]{5}$` | "group_id must match pattern EXG_YYYYMMDD_HHMMSS_xxxxx" |
| `parent_directive_id` | Regex `^EXE_\d{8}_\d{6}_[0-9a-f]{8}$` | "parent_directive_id must be valid ExecutionDirective ID" |
| `order_ids` | Unique IDs in list | "order_ids must contain unique values" |
| `target_quantity` | `> 0` if set | "target_quantity must be positive" |
| `filled_quantity` | `>= 0` if set | "filled_quantity cannot be negative" |

### 3.2 Cross-Field Validation

| **Rule** | **Validation** | **Error Message** |
|----------|--------------|-------------------|
| Fill ratio | `filled_quantity <= target_quantity` | "filled_quantity cannot exceed target_quantity" |
| Final state | NOT (`cancelled_at` AND `completed_at`) | "Group cannot be both cancelled and completed" |
| Status consistency | `status=CANCELLED` ⇒ `cancelled_at` set | "CANCELLED status requires cancelled_at timestamp" |
| Status consistency | `status=COMPLETED` ⇒ `completed_at` set | "COMPLETED status requires completed_at timestamp" |
| Timestamp order | `created_at <= updated_at` | "updated_at cannot be before created_at" |

### 3.3 Strategy-Specific Validation

| **Strategy** | **Required Fields** | **Validation** |
|--------------|-------------------|---------------|
| `TWAP`, `DCA`, `LAYERED` | `target_quantity` | Must be set for quantity-driven strategies |
| `SINGLE` | `order_ids` length == 1 | SINGLE strategy must have exactly 1 order |
| `ICEBERG` | `metadata["visible_ratio"]` | Iceberg must specify visible_ratio in metadata |

---

## 4. Immutability Contract

**ExecutionGroup is MUTABLE** (unlike most DTOs) because it tracks evolving state.

**Allowed Mutations:**
- ✅ `order_ids.append()` - Add new order ID to group
- ✅ `status` updates - Lifecycle transitions
- ✅ `filled_quantity` updates - Track fill progress
- ✅ `updated_at` updates - Audit trail
- ✅ `cancelled_at` / `completed_at` - Final state timestamps

**Forbidden Mutations:**
- ❌ `group_id` - Immutable after creation
- ❌ `parent_directive_id` - Immutable after creation
- ❌ `execution_strategy` - Immutable after creation
- ❌ `created_at` - Immutable after creation
- ❌ `target_quantity` - Immutable after creation (set once)

**Rationale:** ExecutionGroup is a **tracking entity** not a **value object**. State evolution is its core purpose.

---

## 5. Example Instances

### Example 1: TWAP Order Group (Active)

```python
ExecutionGroup(
    group_id="EXG_20251028_143022_a8f3c",
    parent_directive_id="EXE_20251028_143020_b7c4d890",
    execution_strategy=ExecutionStrategyType.TWAP,
    order_ids=["binance_123", "binance_124", "binance_125"],
    status=GroupStatus.ACTIVE,
    created_at=datetime(2025, 10, 28, 14, 30, 22, tzinfo=timezone.utc),
    updated_at=datetime(2025, 10, 28, 14, 35, 15, tzinfo=timezone.utc),
    target_quantity=Decimal("100.0"),
    filled_quantity=Decimal("30.0"),  # 30% filled
    cancelled_at=None,
    completed_at=None,
    metadata={
        "chunk_size": Decimal("10.0"),
        "interval_seconds": 300,
        "total_chunks": 10,
        "chunks_placed": 3
    }
)
```

**Expected Behavior:**
- Fill ratio: 30% (30/100)
- Remaining: 7 chunks (10 - 3)
- Next chunk at: created_at + (3 * 300s) = 14:45:22

### Example 2: Iceberg Order Group (Active)

```python
ExecutionGroup(
    group_id="EXG_20251028_150000_c9e7f",
    parent_directive_id="EXE_20251028_145958_d1a2b3c4",
    execution_strategy=ExecutionStrategyType.ICEBERG,
    order_ids=["binance_200"],  # Only visible order ID (hidden managed by exchange)
    status=GroupStatus.ACTIVE,
    created_at=datetime(2025, 10, 28, 15, 0, 0, tzinfo=timezone.utc),
    updated_at=datetime(2025, 10, 28, 15, 0, 0, tzinfo=timezone.utc),
    target_quantity=Decimal("500.0"),
    filled_quantity=Decimal("0.0"),
    cancelled_at=None,
    completed_at=None,
    metadata={
        "visible_ratio": 0.2,       # Show 20% (100 BTC) at a time
        "refresh_threshold": 0.5,   # Refresh when 50% of visible filled
        "total_refreshes": 0
    }
)
```

### Example 3: Emergency Cancelled Group

```python
ExecutionGroup(
    group_id="EXG_20251028_160000_e2f8g",
    parent_directive_id="EXE_20251028_155958_f3b4c5d6",
    execution_strategy=ExecutionStrategyType.TWAP,
    order_ids=["binance_300", "binance_301"],
    status=GroupStatus.CANCELLED,
    created_at=datetime(2025, 10, 28, 16, 0, 0, tzinfo=timezone.utc),
    updated_at=datetime(2025, 10, 28, 16, 5, 30, tzinfo=timezone.utc),
    target_quantity=Decimal("200.0"),
    filled_quantity=Decimal("40.0"),  # Partial fill before cancel
    cancelled_at=datetime(2025, 10, 28, 16, 5, 30, tzinfo=timezone.utc),
    completed_at=None,
    metadata={
        "cancel_reason": "RISK_THRESHOLD_BREACHED",
        "risk_event_id": "THR_20251028_160530_abc123"
    }
)
```

### Example 4: Completed DCA Group

```python
ExecutionGroup(
    group_id="EXG_20251028_100000_g4h9i",
    parent_directive_id="EXE_20251028_095958_h5c6d7e8",
    execution_strategy=ExecutionStrategyType.DCA,
    order_ids=["binance_400", "binance_401", "binance_402", "binance_403", "binance_404"],
    status=GroupStatus.COMPLETED,
    created_at=datetime(2025, 10, 28, 10, 0, 0, tzinfo=timezone.utc),
    updated_at=datetime(2025, 10, 28, 14, 0, 0, tzinfo=timezone.utc),
    target_quantity=Decimal("50.0"),
    filled_quantity=Decimal("50.0"),  # 100% filled
    cancelled_at=None,
    completed_at=datetime(2025, 10, 28, 14, 0, 0, tzinfo=timezone.utc),
    metadata={
        "frequency": "hourly",
        "amount_per_buy": Decimal("10.0"),
        "total_buys": 5,
        "start_time": "2025-10-28T10:00:00Z",
        "end_time": "2025-10-28T14:00:00Z"
    }
)
```

### Example 5: Single Order (No Grouping)

```python
ExecutionGroup(
    group_id="EXG_20251028_120000_i5j0k",
    parent_directive_id="EXE_20251028_115958_j6d7e8f9",
    execution_strategy=ExecutionStrategyType.SINGLE,
    order_ids=["binance_500"],
    status=GroupStatus.COMPLETED,
    created_at=datetime(2025, 10, 28, 12, 0, 0, tzinfo=timezone.utc),
    updated_at=datetime(2025, 10, 28, 12, 0, 1, tzinfo=timezone.utc),
    target_quantity=Decimal("10.0"),
    filled_quantity=Decimal("10.0"),
    cancelled_at=None,
    completed_at=datetime(2025, 10, 28, 12, 0, 1, tzinfo=timezone.utc),
    metadata=None  # No strategy-specific config needed
)
```

---

## 6. Type System Guarantees

### 6.1 Pydantic Validators

```python
@field_validator("order_ids")
@classmethod
def validate_unique_order_ids(cls, v: list[str]) -> list[str]:
    """Ensure all order IDs are unique."""
    if len(v) != len(set(v)):
        raise ValueError("order_ids must contain unique values")
    return v

@field_validator("filled_quantity")
@classmethod
def validate_fill_ratio(cls, v: Optional[Decimal], info) -> Optional[Decimal]:
    """Ensure filled quantity doesn't exceed target."""
    if v is None:
        return v
    target = info.data.get("target_quantity")
    if target and v > target:
        raise ValueError(
            f"filled_quantity ({v}) cannot exceed target_quantity ({target})"
        )
    return v

@field_validator("cancelled_at")
@classmethod
def validate_final_state_xor(cls, v: Optional[datetime], info) -> Optional[datetime]:
    """Ensure group cannot be both cancelled AND completed."""
    if v and info.data.get("completed_at"):
        raise ValueError("Group cannot be both cancelled and completed")
    return v
```

### 6.2 Type Safety

```python
# Strong typing prevents misuse
group = ExecutionGroup(...)
group.order_ids.append("new_order")  # ✅ OK - list mutation
group.group_id = "new_id"            # ❌ ValidationError - frozen field (if frozen config)
group.status = "INVALID"             # ❌ TypeError - not a GroupStatus enum
```

---

## 7. JSON Schema

```json
{
  "title": "ExecutionGroup",
  "type": "object",
  "properties": {
    "group_id": {
      "type": "string",
      "pattern": "^EXG_\\d{8}_\\d{6}_[0-9a-z]{5}$",
      "description": "Unique execution group ID"
    },
    "parent_directive_id": {
      "type": "string",
      "pattern": "^EXE_\\d{8}_\\d{6}_[0-9a-f]{8}$",
      "description": "Parent ExecutionDirective ID"
    },
    "execution_strategy": {
      "type": "string",
      "enum": ["SINGLE", "TWAP", "VWAP", "ICEBERG", "DCA", "LAYERED", "POV"],
      "description": "Execution strategy type"
    },
    "order_ids": {
      "type": "array",
      "items": {"type": "string"},
      "description": "List of connector order IDs"
    },
    "status": {
      "type": "string",
      "enum": ["PENDING", "ACTIVE", "COMPLETED", "CANCELLED", "FAILED", "PARTIAL"],
      "description": "Group lifecycle status"
    },
    "created_at": {
      "type": "string",
      "format": "date-time",
      "description": "Group creation timestamp (UTC)"
    },
    "updated_at": {
      "type": "string",
      "format": "date-time",
      "description": "Last update timestamp (UTC)"
    },
    "target_quantity": {
      "type": ["string", "null"],
      "description": "Target quantity (Decimal as string)"
    },
    "filled_quantity": {
      "type": ["string", "null"],
      "description": "Filled quantity (Decimal as string)"
    },
    "cancelled_at": {
      "type": ["string", "null"],
      "format": "date-time",
      "description": "Cancellation timestamp"
    },
    "completed_at": {
      "type": ["string", "null"],
      "format": "date-time",
      "description": "Completion timestamp"
    },
    "metadata": {
      "type": ["object", "null"],
      "description": "Strategy-specific metadata (JSON)"
    }
  },
  "required": ["group_id", "parent_directive_id", "execution_strategy", "order_ids", "status", "created_at", "updated_at"]
}
```

---

## 8. Test Coverage Requirements

### Minimum 20 Tests:

**Creation Tests (3):**
1. `test_create_execution_group_minimal` - Only required fields
2. `test_create_execution_group_full` - All fields populated
3. `test_create_execution_group_with_metadata` - Strategy-specific metadata

**Validation Tests (6):**
4. `test_group_id_format_validation` - Invalid pattern rejected
5. `test_parent_directive_id_format_validation` - Invalid pattern rejected
6. `test_unique_order_ids_validation` - Duplicate order IDs rejected
7. `test_fill_ratio_validation` - filled > target rejected
8. `test_final_state_xor_validation` - Both cancelled_at AND completed_at rejected
9. `test_target_quantity_positive_validation` - Negative target rejected

**Strategy Tests (7):**
10. `test_execution_strategy_single` - SINGLE strategy
11. `test_execution_strategy_twap` - TWAP with chunks
12. `test_execution_strategy_iceberg` - ICEBERG with visible_ratio
13. `test_execution_strategy_dca` - DCA with frequency
14. `test_execution_strategy_vwap` - VWAP strategy
15. `test_execution_strategy_layered` - LAYERED limits
16. `test_execution_strategy_pov` - POV strategy

**Status Tests (6):**
17. `test_status_pending_to_active` - Status transition
18. `test_status_active_to_completed` - Successful completion
19. `test_status_active_to_cancelled` - Emergency cancel
20. `test_status_active_to_failed` - Execution failure
21. `test_status_active_to_partial` - Partial fill stop
22. `test_status_consistency_validation` - Status-timestamp consistency

**Mutation Tests (2):**
23. `test_order_ids_append_mutation` - Add order to group
24. `test_filled_quantity_update_mutation` - Update fill progress

**Serialization Tests (1):**
25. `test_json_serialization_roundtrip` - model_dump() → model_validate()

---

## 9. Dependencies & Integration

### 9.1 Dependencies (Imports)

```python
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from backend.utils.id_generators import generate_execution_group_id
```

### 9.2 Integration Points

| **Component** | **Relationship** | **Purpose** |
|--------------|-----------------|-------------|
| `ExecutionDirective` | Parent (1:N) | directive → multiple groups |
| `ExecutionHandler` | Consumer | Creates/updates groups during execution |
| `IStrategyLedger` | Provider | `get_execution_groups()`, `cancel_execution_group()` |
| `PositionTracker` | Observer | Aggregates fills from group orders |
| `PortfolioMonitor` | Observer | Monitors group PnL and risk |

---

## 10. Breaking Changes

**None** - ExecutionGroup is a NEW DTO in v4.0.

No migration needed from v3.0 (no equivalent existed).

---

## 11. Quality Criteria (Definition of Done)

- ✅ All 25 tests passing (100% coverage)
- ✅ Pylint 10/10 score (no warnings)
- ✅ Type checking: 0 Pylance errors
- ✅ Pydantic validators implemented (unique order_ids, fill ratio, XOR final state)
- ✅ Comprehensive docstrings (module, class, all fields)
- ✅ JSON schema examples (5 examples in model_config)
- ✅ ID generator `generate_execution_group_id()` implemented
- ✅ Export in `backend/dtos/execution/__init__.py`
- ✅ Quality Metrics Dashboard updated

---

## 12. Decision Log

### Decision 1: Mutable vs Immutable

**Question:** Should ExecutionGroup be frozen (immutable)?  
**Decision:** NO - ExecutionGroup is **mutable**  
**Rationale:**
- ExecutionGroup is a **tracking entity**, not a value object
- Core purpose is state evolution (order_ids append, status updates, fill progress)
- Immutability would require creating new instances on every order placement (wasteful)
- Contrast with ExecutionIntent (immutable value object expressing intent)

**Trade-offs:**
- ✅ Pro: Natural API for state updates (`group.order_ids.append()`)
- ✅ Pro: Memory efficient (single instance updated in-place)
- ❌ Con: Thread safety concerns (requires locking in concurrent env)
- ❌ Con: No immutable audit trail (must log changes externally)

### Decision 2: Separate Enums vs Single Status Field

**Question:** Use separate booleans (`is_cancelled`, `is_completed`) or single enum?  
**Decision:** Single `GroupStatus` enum  
**Rationale:**
- State machine is mutually exclusive (group cannot be ACTIVE AND CANCELLED)
- Enum prevents invalid states (no boolean combination bugs)
- Clear lifecycle transitions (PENDING → ACTIVE → COMPLETED/CANCELLED/FAILED)
- Easier to extend (add PAUSED, RETRYING states later)

### Decision 3: target_quantity/filled_quantity vs Generic Metrics

**Question:** Hardcode quantity fields or use generic `metrics: dict`?  
**Decision:** Explicit `target_quantity` and `filled_quantity` fields  
**Rationale:**
- Fill ratio is a **universal metric** across all quantity-based strategies
- Type safety: Decimal precision for financial quantities
- Validation: Can enforce filled <= target at Pydantic level
- Queryability: Can filter groups by fill_ratio in database

**Trade-offs:**
- ✅ Pro: Type-safe, validated, queryable
- ✅ Pro: Clear API (`group.filled_quantity` vs `group.metrics["filled"]`)
- ❌ Con: Less flexible for non-quantity strategies (use metadata for custom metrics)

---

## 13. Next Steps

### STAP 1 RED: Write Failing Tests
**File:** `tests/unit/dtos/execution/test_execution_group.py`  
**Action:** Create 25 failing tests based on Section 8 requirements  
**Expected:** `ModuleNotFoundError: No module named 'backend.dtos.execution.execution_group'`

### STAP 2 GREEN: Implement DTO
**File:** `backend/dtos/execution/execution_group.py`  
**Action:**
1. Create `ExecutionStrategyType` enum (7 values)
2. Create `GroupStatus` enum (6 values)
3. Create `ExecutionGroup` Pydantic BaseModel (12 fields)
4. Implement 3 Pydantic validators (unique order_ids, fill ratio, XOR final state)
5. Add `generate_execution_group_id()` to `id_generators.py`
6. Export in `backend/dtos/execution/__init__.py`
7. Run tests → ALL GREEN ✅

### STAP 3 REFACTOR: Quality & Documentation
**Action:**
1. Pylint → 10/10 score (trailing whitespace, imports, line length)
2. Add 5 JSON schema examples to `model_config`
3. Comprehensive docstrings (module header, class, all fields)
4. Update Quality Metrics Dashboard in `agent.md`
5. Final test run → 25/25 passing ✅

---

**END OF CONCEPTUAL DESIGN**
