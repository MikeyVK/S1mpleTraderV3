<!-- filepath: docs/development/backend/dtos/EXECUTION_COMMAND_BATCH_DESIGN.md -->
# ExecutionCommandBatch Design Document

**Status:** ⚠️ Pending Refactor  
**Version:** 1.0  
**Last Updated:** 2025-12-07

---

## 1. Identity

| Aspect | Value |
|--------|-------|
| **DTO Name** | ExecutionCommandBatch |
| **ID Prefix** | `BAT_` |
| **Layer** | Execution |
| **File Path** | `backend/dtos/execution/execution_command.py` (combined with ExecutionCommand) |
| **Status** | ⚠️ Pending refactor |

---

## 2. Contract

| Role | Component |
|------|-----------|
| **Producer** | ExecutionPlanner (boilerplate aggregation) |
| **Consumer(s)** | ExecutionWorker |
| **Trigger** | All ExecutionCommands aggregated for a StrategyDirective |

**Architectural Role:**
- Wraps 1-N ExecutionCommands for coordinated execution
- **1:1 relationship with StrategyDirective** (one directive = one batch)
- Multiplicity of commands comes from `target_plan_ids` in StrategyDirective
- Aggregation is "dumb pipe" - no logic, only 1-on-1 mapping from ExecutionPolicy

---

## 3. Fields

### 3.1 Current Fields

| Field | Type | Req | Producer | Consumer | Status |
|-------|------|-----|----------|----------|--------|
| `batch_id` | `str` | ✅ | Auto-generated | ExecutionWorker | ✅ Keep |
| `commands` | `list[ExecutionCommand]` | ✅ | ExecutionPlanner | ExecutionWorker | ✅ Keep |
| `created_at` | `datetime` | ✅ | ExecutionPlanner | ExecutionWorker | ✅ Keep |
| `execution_mode` | `ExecutionMode` | ✅ | ??? | ExecutionWorker | ⚠️ Rename to `mode` |
| `rollback_on_failure` | `bool` | ✅ | ??? | ExecutionWorker | ❌ Remove |
| `timeout_seconds` | `int \| None` | ❌ | ??? | ExecutionWorker | ✅ Keep |
| `metadata` | `dict[str, Any] \| None` | ❌ | ??? | - | ❌ Remove (code smell) |

### 3.2 Target Fields (Post-Refactor)

| Field | Type | Req | Source | Validation |
|-------|------|-----|--------|------------|
| `batch_id` | `str` | ✅ | Auto-generated | Pattern: `^BAT_\d{8}_\d{6}_[0-9a-z]{5,8}$` |
| `commands` | `list[ExecutionCommand]` | ✅ | ExecutionPlanner | min_length=1 |
| `created_at` | `datetime` | ✅ | Auto-generated | UTC, timezone-aware |
| `mode` | `BatchExecutionMode` | ✅ | ExecutionPolicy | Enum value |
| `timeout_seconds` | `int \| None` | ❌ | ExecutionPolicy | > 0 if provided |

---

## 4. Causality

| Aspect | Value |
|--------|-------|
| **Category** | **Post-causality** (aggregation container) |
| **Has causality field** | ❌ **NO** - causality is in each ExecutionCommand |
| **ID tracked in CausalityChain** | `execution_command_batch_id` (TBD) |

**Note:** Each ExecutionCommand in the batch contains its own CausalityChain. The batch is a coordination wrapper, not a causality carrier.

---

## 5. Immutability

| Decision | Rationale |
|----------|-----------|
| **frozen** | `True` |
| **Why** | Batch integrity during execution - cannot be modified once created. |

---

## 6. Examples

### Single Command Batch (N=1)
```json
{
  "batch_id": "BAT_20251207_143022_a8f3c",
  "commands": [
    {
      "command_id": "EXC_20251207_143020_1a2b3c4d",
      "causality": { "origin": {"id": "TCK_...", "type": "TICK"} }
    }
  ],
  "mode": "INDEPENDENT",
  "created_at": "2025-12-07T14:30:22Z",
  "timeout_seconds": null
}
```

### Multi-Command Batch - Pair Trade (N=2)
```json
{
  "batch_id": "BAT_20251207_150000_b9c4d",
  "commands": [
    {
      "command_id": "EXC_20251207_150001_2b3c4d5e",
      "causality": { "origin": {"id": "TCK_...", "type": "TICK"} }
    },
    {
      "command_id": "EXC_20251207_150002_3c4d5e6f",
      "causality": { "origin": {"id": "TCK_...", "type": "TICK"} }
    }
  ],
  "mode": "COORDINATED",
  "created_at": "2025-12-07T15:00:00Z",
  "timeout_seconds": 30
}
```

---

## 7. Dependencies

- `backend/dtos/execution/execution_command.py` → `ExecutionCommand`
- `backend/core/enums.py` → `BatchExecutionMode` (NEW)
- `backend/utils/id_generators.py` → `generate_batch_id()`
- `pydantic.BaseModel`

---

## 8. Architecture Decision: ExecutionPolicy

**Decision Date:** 2025-12-07

### 8.1 Problem Statement

Batch coordination fields (`execution_mode`, `rollback_on_failure`, `timeout_seconds`) had no clear origin. Documentation said "PlanningAggregator sets based on StrategyDirective", but:
1. PlanningAggregator does not exist as a component (aggregation is boilerplate)
2. StrategyDirective had no fields for batch coordination
3. `metadata: dict[str, Any]` is a code smell

### 8.2 Solution: ExecutionPolicy in StrategyDirective

Batch coordination parameters originate from `ExecutionPolicy` in `StrategyDirective`.

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

### 8.3 BatchExecutionMode Enum

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

### 8.4 Dumb Pipe Aggregation

The aggregation code (boilerplate in BaseExecutionPlanner) does **no decisions** - only 1-on-1 mapping:

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

### 8.5 Quant Scenario Validation

| Scenario | Policy | Mode | Behavior |
|----------|--------|------|----------|
| Flash Crash (close 3 positions) | None (default) | INDEPENDENT | Fire all, ignore failures |
| Pair Trade (long A, short B) | `mode=COORDINATED` | COORDINATED | Fire all, cancel others on failure |
| DCA (3 limit orders) | None (default) | INDEPENDENT | Fire all limits |
| Rotation (sell A, then buy B) | `mode=SEQUENTIAL` | SEQUENTIAL | One by one, stop on failure |

---

## 9. Design Decisions

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

### Why Remove rollback_on_failure?
- Implicit in mode definition:
  - INDEPENDENT → no rollback (ignore failures)
  - COORDINATED → rollback (cancel/revert on failure)
  - SEQUENTIAL → stop (no rollback, just halt)

---

## 10. Implementation Tasks

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

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-07 | AI Agent | Initial design with ExecutionPolicy architecture decision |
