# ExecutionDirectiveBatch DTO - Conceptueel Ontwerp (STAP 0)

**Status:** Architectural Contract  
**Versie:** 1.0  
**Datum:** 2025-10-28  
**Owner:** Platform Architecture Team

---

## Executive Summary

**ExecutionDirectiveBatch** is het DTO voor atomic multi-directive execution. Het biedt **all-or-nothing execution** voor scenario's zoals emergency exits, portfolio rebalancing, en hedging operations. Ondersteunt 3 execution modes: SEQUENTIAL (stop on failure), PARALLEL (simultaneous), en ATOMIC (rollback on any failure).

**Kernprincipe:**
> ExecutionDirectiveBatch is de "transaction coordinator" - execute multiple directives with atomic guarantees.

---

## 1. Architectural Contract

### 1.1 Responsibility (SRP)

**ExecutionDirectiveBatch heeft ÉÉN verantwoordelijkheid:**
> "Coordinate atomic execution of multiple ExecutionDirectives with rollback support"

**NIET verantwoordelijk voor:**
- ❌ Individual directive execution (dat is ExecutionHandler's domein)
- ❌ Order placement (dat is ExecutionTranslator's domein)
- ❌ State persistence (dat is IStrategyLedger's domein)
- ❌ Error recovery strategies (dat is ErrorHandler's domein)

### 1.2 Core Use Cases

1. **Emergency Exit**: Sluit 5 posities ALL-OR-NOTHING bij flash crash
2. **Portfolio Rebalance**: 10 modifications (ATOMIC - all succeed or rollback)
3. **Hedging Operation**: Open hedge + close position (SEQUENTIAL - stop on failure)
4. **Batch Cancellations**: Cancel 20 orders simultaneously (PARALLEL)
5. **Multi-Leg Strategy**: Options spread (4 legs ATOMIC)

### 1.3 Field Specification

| **Field** | **Type** | **Required** | **Description** | **Example** |
|-----------|----------|--------------|-----------------|-------------|
| `batch_id` | `str` | ✅ Yes | Unique batch ID (pattern: `BAT_YYYYMMDD_HHMMSS_xxxxx`) | `"BAT_20251028_143022_a8f3c"` |
| `directives` | `list[ExecutionDirective]` | ✅ Yes | List of directives to execute | `[directive1, directive2]` |
| `execution_mode` | `ExecutionMode` | ✅ Yes | Execution mode (SEQUENTIAL, PARALLEL, ATOMIC) | `ExecutionMode.ATOMIC` |
| `created_at` | `datetime` | ✅ Yes | Batch creation timestamp (UTC) | `2025-10-28T14:30:22Z` |
| `rollback_on_failure` | `bool` | ❌ No | Rollback all on any failure (default: True for ATOMIC) | `True` |
| `timeout_seconds` | `Optional[int]` | ❌ No | Max execution time (None = no timeout) | `30` |
| `metadata` | `Optional[dict]` | ❌ No | Batch-specific metadata (JSON) | `{"reason": "FLASH_CRASH"}` |

### 1.4 Enums

#### ExecutionMode
```python
class ExecutionMode(str, Enum):
    """Batch execution mode."""
    SEQUENTIAL = "SEQUENTIAL"  # Execute 1-by-1, stop on first failure
    PARALLEL = "PARALLEL"      # Execute all simultaneously (no rollback)
    ATOMIC = "ATOMIC"          # All succeed or all rollback (transaction)
```

---

## 2. Field-by-Field Specification

### 2.1 batch_id (str)

**Purpose:** Unique identifier for execution batch  
**Format:** `BAT_YYYYMMDD_HHMMSS_xxxxx` (military datetime + 5-8 char hash)  
**Generated:** Via `generate_batch_id()` in `id_generators.py`  
**Validation:** Regex pattern `^BAT_\d{8}_\d{6}_[0-9a-z]{5,8}$`

**Example:**
```python
batch_id="BAT_20251028_143022_a8f3c"
```

### 2.2 directives (List[ExecutionDirective])

**Purpose:** List of directives to execute as batch  
**Constraints:**
- Minimum: 1 directive (empty list rejected)
- Maximum: None (maar praktisch max ~100 voor performance)
- All directives must be valid ExecutionDirective instances

**Validation:**
- `validate_non_empty_directives`: Reject empty list
- `validate_unique_directive_ids`: All directive_ids must be unique

**Example:**
```python
directives=[
    ExecutionDirective(directive_id="EXE_..._1", ...),
    ExecutionDirective(directive_id="EXE_..._2", ...),
    ExecutionDirective(directive_id="EXE_..._3", ...)
]
```

### 2.3 execution_mode (ExecutionMode)

**Purpose:** Defines how directives are executed  

**Modes:**

1. **SEQUENTIAL**: Execute directives 1-by-1 in list order
   - Stop on first failure
   - No automatic rollback
   - Use case: Hedging operations (open hedge BEFORE closing position)

2. **PARALLEL**: Execute all directives simultaneously
   - Best-effort execution
   - No rollback on partial failures
   - Use case: Batch cancellations (speed > atomicity)

3. **ATOMIC**: All-or-nothing transaction
   - All succeed OR all rollback
   - Slowest but safest
   - Use case: Emergency exits, portfolio rebalance

**Example:**
```python
execution_mode=ExecutionMode.ATOMIC
```

### 2.4 created_at (datetime)

**Purpose:** Batch creation timestamp (UTC)  
**Timezone:** MUST be timezone-aware (UTC)  
**Auto-generated:** Via `datetime.now(timezone.utc)` at batch creation

**Example:**
```python
created_at=datetime(2025, 10, 28, 14, 30, 22, tzinfo=timezone.utc)
```

### 2.5 rollback_on_failure (bool, optional)

**Purpose:** Enable automatic rollback on any failure  
**Default:**
- `True` for `ExecutionMode.ATOMIC`
- `False` for `ExecutionMode.SEQUENTIAL` and `PARALLEL`

**Validation:** Must be `True` if `execution_mode == ATOMIC`

**Example:**
```python
rollback_on_failure=True
```

### 2.6 timeout_seconds (Optional[int])

**Purpose:** Maximum execution time for entire batch  
**Default:** `None` (no timeout)  
**Validation:** If set, must be positive integer

**Example:**
```python
timeout_seconds=30  # Max 30 seconds for batch completion
```

### 2.7 metadata (Optional[Dict[str, Any]])

**Purpose:** Batch-specific context and metadata  
**Format:** JSON-serializable dict  
**Use cases:**
- Emergency reason: `{"reason": "FLASH_CRASH", "trigger_price": 45000}`
- Rebalance context: `{"target_allocation": {"BTC": 0.6, "ETH": 0.4}}`
- User context: `{"user_id": "user_123", "action": "MANUAL_EXIT"}`

**Example:**
```python
metadata={"reason": "FLASH_CRASH", "risk_threshold": 0.05}
```

---

## 3. Validation Rules

### 3.1 Pydantic Validators

```python
@field_validator("batch_id")
def validate_batch_id_format(cls, v: str) -> str:
    """Ensure batch_id matches BAT_YYYYMMDD_HHMMSS_xxxxx format."""
    pattern = r"^BAT_\d{8}_\d{6}_[0-9a-z]{5,8}$"
    if not match(pattern, v):
        raise ValueError(f"batch_id must match pattern BAT_YYYYMMDD_HHMMSS_xxxxx, got: {v}")
    return v

@field_validator("directives")
def validate_non_empty_directives(cls, v: List[ExecutionDirective]) -> List[ExecutionDirective]:
    """Ensure directives list is not empty."""
    if len(v) == 0:
        raise ValueError("directives list cannot be empty (minimum 1 directive required)")
    return v

@field_validator("directives")
def validate_unique_directive_ids(cls, v: List[ExecutionDirective]) -> List[ExecutionDirective]:
    """Ensure all directive IDs are unique within batch."""
    directive_ids = [d.directive_id for d in v]
    if len(directive_ids) != len(set(directive_ids)):
        raise ValueError("All directive_ids must be unique within batch (duplicates found)")
    return v

@field_validator("rollback_on_failure")
def validate_atomic_rollback(cls, v: bool, info: ValidationInfo) -> bool:
    """Ensure rollback_on_failure=True for ATOMIC mode."""
    execution_mode: Optional[ExecutionMode] = info.data.get("execution_mode")
    if execution_mode == ExecutionMode.ATOMIC and not v:
        raise ValueError("rollback_on_failure must be True for ExecutionMode.ATOMIC")
    return v

@field_validator("timeout_seconds")
def validate_timeout_positive(cls, v: Optional[int]) -> Optional[int]:
    """Ensure timeout_seconds is positive if provided."""
    if v is not None and v <= 0:
        raise ValueError(f"timeout_seconds must be positive, got: {v}")
    return v
```

---

## 4. Mutability Contract

**ExecutionDirectiveBatch is IMMUTABLE** (`frozen=True`):
- Once created, fields CANNOT be modified
- Use case: Ensures batch integrity during execution
- If changes needed: Create new batch (don't modify existing)

**Rationale:**
- Batch execution is atomic operation (immutability prevents mid-execution changes)
- Audit trail preservation (original batch state preserved)
- Thread-safety (no concurrent modification issues)

---

## 5. Example Instances

### 5.1 Example: Emergency Exit (ATOMIC mode)

```python
from datetime import datetime, timezone
from backend.dtos.execution.execution_directive import ExecutionDirective
from backend.dtos.execution.execution_directive_batch import (
    ExecutionDirectiveBatch,
    ExecutionMode
)

# Emergency scenario: Close 3 positions ALL-OR-NOTHING
batch = ExecutionDirectiveBatch(
    batch_id="BAT_20251028_143022_a8f3c",
    directives=[
        ExecutionDirective(
            directive_id="EXE_20251028_143020_b7c4d",
            # ... BTC position close ...
        ),
        ExecutionDirective(
            directive_id="EXE_20251028_143021_c8e9f",
            # ... ETH position close ...
        ),
        ExecutionDirective(
            directive_id="EXE_20251028_143022_d1a2b",
            # ... SOL position close ...
        )
    ],
    execution_mode=ExecutionMode.ATOMIC,
    created_at=datetime(2025, 10, 28, 14, 30, 22, tzinfo=timezone.utc),
    rollback_on_failure=True,  # Required for ATOMIC
    timeout_seconds=30,
    metadata={
        "reason": "FLASH_CRASH",
        "trigger_price": 45000,
        "risk_threshold": 0.05
    }
)
```

**Expected Behavior:**
- All 3 positions close successfully OR none close
- If ANY directive fails → rollback all
- Timeout after 30 seconds

### 5.2 Example: Batch Cancellations (PARALLEL mode)

```python
# Cancel 20 pending orders simultaneously
batch = ExecutionDirectiveBatch(
    batch_id="BAT_20251028_150000_e3f4g",
    directives=[
        # 20 CANCEL_ORDER directives
        ExecutionDirective(directive_id="EXE_20251028_150001_f5g6h", ...),
        ExecutionDirective(directive_id="EXE_20251028_150002_g7h8i", ...),
        # ... 18 more ...
    ],
    execution_mode=ExecutionMode.PARALLEL,
    created_at=datetime(2025, 10, 28, 15, 0, 0, tzinfo=timezone.utc),
    rollback_on_failure=False,  # Best-effort (speed > atomicity)
    timeout_seconds=10,
    metadata={"action": "BULK_CANCEL", "count": 20}
)
```

**Expected Behavior:**
- All 20 cancellations execute simultaneously
- Some may fail (orders already filled)
- No rollback on partial failures

### 5.3 Example: Hedging Operation (SEQUENTIAL mode)

```python
# Open hedge BEFORE closing position (order matters)
batch = ExecutionDirectiveBatch(
    batch_id="BAT_20251028_160000_h9i0j",
    directives=[
        # 1. Open hedge position FIRST
        ExecutionDirective(directive_id="EXE_20251028_160001_j1k2l", ...),
        # 2. THEN close main position (only if hedge succeeded)
        ExecutionDirective(directive_id="EXE_20251028_160002_k3l4m", ...)
    ],
    execution_mode=ExecutionMode.SEQUENTIAL,
    created_at=datetime(2025, 10, 28, 16, 0, 0, tzinfo=timezone.utc),
    rollback_on_failure=False,  # Stop on failure, no rollback
    metadata={"strategy": "HEDGED_EXIT"}
)
```

**Expected Behavior:**
- Execute directive 1 (open hedge)
- If successful → execute directive 2 (close position)
- If directive 1 fails → STOP (don't execute directive 2)
- No automatic rollback

---

## 6. JSON Schema (OpenAPI)

```json
{
  "ExecutionDirectiveBatch": {
    "type": "object",
    "required": ["batch_id", "directives", "execution_mode", "created_at"],
    "properties": {
      "batch_id": {
        "type": "string",
        "pattern": "^BAT_\\d{8}_\\d{6}_[0-9a-z]{5,8}$",
        "example": "BAT_20251028_143022_a8f3c"
      },
      "directives": {
        "type": "array",
        "items": {"$ref": "#/components/schemas/ExecutionDirective"},
        "minItems": 1,
        "example": [
          {"directive_id": "EXE_20251028_143020_b7c4d", "...": "..."},
          {"directive_id": "EXE_20251028_143021_c8e9f", "...": "..."}
        ]
      },
      "execution_mode": {
        "type": "string",
        "enum": ["SEQUENTIAL", "PARALLEL", "ATOMIC"],
        "example": "ATOMIC"
      },
      "created_at": {
        "type": "string",
        "format": "date-time",
        "example": "2025-10-28T14:30:22Z"
      },
      "rollback_on_failure": {
        "type": "boolean",
        "default": true,
        "example": true
      },
      "timeout_seconds": {
        "type": "integer",
        "minimum": 1,
        "nullable": true,
        "example": 30
      },
      "metadata": {
        "type": "object",
        "nullable": true,
        "example": {"reason": "FLASH_CRASH", "risk_threshold": 0.05}
      }
    }
  }
}
```

---

## 7. Test Coverage Requirements

**Minimum: 15+ tests** across 6 categories:

### 7.1 Creation Tests (3 tests)
- ✅ `test_create_batch_minimal`: Only required fields
- ✅ `test_create_batch_full`: All fields populated
- ✅ `test_create_batch_with_metadata`: Custom metadata

### 7.2 Validation Tests (6 tests)
- ✅ `test_batch_id_format_validation`: Invalid format rejected
- ✅ `test_empty_directives_rejected`: Empty list raises ValidationError
- ✅ `test_duplicate_directive_ids_rejected`: Duplicate IDs rejected
- ✅ `test_atomic_requires_rollback`: ATOMIC mode requires rollback_on_failure=True
- ✅ `test_timeout_positive_validation`: Negative timeout rejected
- ✅ `test_zero_timeout_rejected`: Zero timeout rejected

### 7.3 Execution Mode Tests (3 tests)
- ✅ `test_sequential_mode`: SEQUENTIAL batch creation
- ✅ `test_parallel_mode`: PARALLEL batch creation
- ✅ `test_atomic_mode`: ATOMIC batch creation with rollback=True

### 7.4 Immutability Tests (1 test)
- ✅ `test_batch_immutability`: Frozen model (cannot modify fields)

### 7.5 Serialization Tests (1 test)
- ✅ `test_json_serialization_roundtrip`: model_dump() → model_validate()

### 7.6 Edge Cases (1 test)
- ✅ `test_single_directive_batch`: Batch with only 1 directive (valid)

---

## 8. Dependencies

**Internal:**
- `backend.dtos.execution.execution_directive.ExecutionDirective`
- `backend.utils.id_generators.generate_batch_id()`

**External:**
- `pydantic` (BaseModel, field_validator)
- `datetime` (timezone-aware timestamps)
- `enum` (ExecutionMode)

---

## 9. Breaking Changes from v3.0

**None** - Dit is een NIEUWE DTO in v4.0 architecture.

**Migration Path:** N/A (geen v3 equivalent)

---

## 10. Quality Gates

**STAP 1 RED:**
- ✅ 15+ failing tests geschreven
- ✅ ModuleNotFoundError confirmed (DTO doesn't exist yet)

**STAP 2 GREEN:**
- ✅ ExecutionMode enum implemented
- ✅ ExecutionDirectiveBatch BaseModel implemented
- ✅ 5 field_validators implemented
- ✅ All 15+ tests PASSING

**STAP 3 REFACTOR:**
- ✅ Pylint 10.00/10 (DTO file)
- ✅ Pylint 10.00/10 (test file)
- ✅ 0 Pylance warnings
- ✅ 3 JSON schema examples in model_config
- ✅ Quality Metrics Dashboard updated

---

## 11. Decision Log

### Decision 1: Immutability (frozen=True)
**Rationale:** Batch execution is atomic operation. Immutability:
- Prevents mid-execution modifications
- Preserves audit trail
- Ensures thread-safety

**Alternative Rejected:** Mutable batch (frozen=False)
- Risk: Mid-execution changes could break atomicity
- Complexity: Need state synchronization

**Chosen:** IMMUTABLE (frozen=True)

### Decision 2: Minimum Directives = 1
**Rationale:** 
- Single-directive batches are valid (simplifies API)
- Use case: Conditional execution (may have 1-N directives)
- No performance penalty

**Alternative Rejected:** Minimum = 2
- Would force artificial batching for single directives
- Complicates conditional batch creation logic

**Chosen:** Minimum = 1 directive

### Decision 3: No Maximum Directives
**Rationale:**
- Platform doesn't enforce hard limit
- ExecutionHandler can implement soft limits
- Flexibility for high-frequency scenarios

**Alternative Rejected:** Hard limit (e.g., max 100)
- Arbitrary restriction
- Use cases vary widely

**Chosen:** No hard maximum (soft limit via timeout)

---

## 12. Next Steps

**After STAP 3 (this DTO complete):**
1. IStrategyLedger Interface definition (track batches)
2. ExecutionTranslator Layer (execute batches)
3. Update ExecutionDirective (add batch_id field)

**Dependencies for Implementation:**
- ExecutionDirective DTO (already exists)
- generate_batch_id() in id_generators.py (needs creation)

**Future Enhancements (v5.0):**
- Retry policies per directive
- Partial rollback (rollback specific directives only)
- Batch priority levels (HIGH, NORMAL, LOW)
