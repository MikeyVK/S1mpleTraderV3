# ExecutionPolicy Design

**Status:** Architecture Decision  
**Datum:** 2025-12-07  
**Context:** ExecutionCommandBatch field origin resolution

---

## 1. Problem Statement

`ExecutionCommandBatch` bevat velden (`execution_mode`, `rollback_on_failure`, `timeout_seconds`, `metadata`) zonder duidelijke origin. De documentatie zei "PlanningAggregator sets based on StrategyDirective", maar:

1. PlanningAggregator bestaat niet als component (aggregatie is boilerplate)
2. StrategyDirective had geen velden voor batch coördinatie
3. `metadata: dict[str, Any]` is een code smell

---

## 2. Architecture Decision

### 2.1 Core Principle: StrategyDirective ↔ ExecutionCommandBatch = 1:1

Elke `StrategyDirective` resulteert in exact één `ExecutionCommandBatch`. De multipliciteit van commands binnen een batch komt uit `target_plan_ids`.

```
StrategyDirective(target_plan_ids=[A, B, C])
    ↓
ExecutionCommandBatch(commands=[EC_A, EC_B, EC_C])
```

### 2.2 ExecutionPolicy: Strategische Batch Coördinatie

We introduceren `ExecutionPolicy` als optioneel veld in `StrategyDirective`. Dit is geen "Directive" (opdracht aan planner), maar een **Policy** (regelset voor uitvoering).

```python
class ExecutionPolicy(BaseModel):
    """
    Defines how a group of trades should be coordinated.
    
    This is NOT a directive to a planner - it's a policy that travels
    unchanged through the pipeline to ExecutionWorker.
    """
    mode: BatchExecutionMode = BatchExecutionMode.INDEPENDENT
    timeout_seconds: int | None = None
```

### 2.3 BatchExecutionMode Enum

```python
class BatchExecutionMode(str, Enum):
    """
    Coordination mode for multiple commands in a batch.
    
    Values:
        INDEPENDENT: Fire all, ignore failures of others (default)
                     Use case: Flash crash close, DCA entries
        COORDINATED: Fire all, if one fails, cancel/revert others
                     Use case: Pair trades, hedged positions
        SEQUENTIAL:  Fire one by one, stop if one fails
                     Use case: Rotation strategies, dependent entries
    """
    INDEPENDENT = "INDEPENDENT"
    COORDINATED = "COORDINATED"
    SEQUENTIAL = "SEQUENTIAL"
```

### 2.4 Dumb Pipe Aggregation

De aggregatie code (boilerplate in BaseExecutionPlanner) doet **geen beslissingen** - alleen 1-op-1 mapping:

```python
# Boilerplate - NO LOGIC, just mapping
def create_batch(
    self, 
    directive: StrategyDirective, 
    commands: list[ExecutionCommand]
) -> ExecutionCommandBatch:
    
    policy = directive.execution_policy or ExecutionPolicy()
    
    return ExecutionCommandBatch(
        commands=commands,
        mode=policy.mode,                    # Direct copy
        timeout_seconds=policy.timeout_seconds  # Direct copy
    )
```

---

## 3. DTO Changes

### 3.1 StrategyDirective (Add)

```python
class StrategyDirective(BaseModel):
    # ... existing fields ...
    
    # NEW: Batch coordination policy
    execution_policy: ExecutionPolicy | None = Field(
        default=None,
        description="Optional batch coordination policy. If None, INDEPENDENT mode is used."
    )
```

### 3.2 ExecutionCommandBatch (Modify)

```python
class ExecutionCommandBatch(BaseModel):
    batch_id: str
    commands: list[ExecutionCommand]
    created_at: datetime
    
    # RENAMED: execution_mode → mode
    mode: BatchExecutionMode
    
    # KEPT: timeout_seconds (from policy)
    timeout_seconds: int | None = None
    
    # REMOVED: metadata (code smell)
    # REMOVED: rollback_on_failure (implicit in mode)
```

---

## 4. Quant Scenario Validation

| Scenario | Policy | Mode | Behavior |
|----------|--------|------|----------|
| Flash Crash (close 3 positions) | None (default) | INDEPENDENT | Fire all, ignore failures |
| Pair Trade (long A, short B) | `mode=COORDINATED` | COORDINATED | Fire all, cancel others on failure |
| DCA (3 limit orders) | None (default) | INDEPENDENT | Fire all limits |
| Rotation (sell A, then buy B) | `mode=SEQUENTIAL` | SEQUENTIAL | One by one, stop on failure |

---

## 5. Implementation Checklist

- [ ] Add `BatchExecutionMode` to `backend/core/enums.py`
- [ ] Create `ExecutionPolicy` class in `backend/dtos/strategy/strategy_directive.py`
- [ ] Add `execution_policy` field to `StrategyDirective`
- [ ] Modify `ExecutionCommandBatch`:
  - [ ] Rename `execution_mode` → `mode`
  - [ ] Change type to `BatchExecutionMode`
  - [ ] Remove `metadata` field
  - [ ] Remove `rollback_on_failure` field
- [ ] Update all tests
- [ ] Update `DTO_ARCHITECTURE.md`

---

## 6. Rationale

### Why Policy, not Directive?

- **Directives** are instructions to planners (hints → concrete plans)
- **Policies** are rules that travel unchanged (no transformation)
- Batch coordination doesn't need a "BatchPlanner" - it's a direct instruction

### Why INDEPENDENT as Default?

- Safe default: failures don't cascade
- Most common case: single trade (N=1) or unrelated trades
- Explicit opt-in for COORDINATED/SEQUENTIAL

### Why Remove metadata?

- `dict[str, Any]` violates type safety
- Use cases (FLASH_CRASH reason) belong in Journal, not DTO
- If needed: create typed fields with explicit purpose

### Why Remove rollback_on_failure?

- Implicit in mode definition:
  - INDEPENDENT → no rollback (ignore failures)
  - COORDINATED → rollback (cancel/revert on failure)
  - SEQUENTIAL → stop (no rollback, just halt)
