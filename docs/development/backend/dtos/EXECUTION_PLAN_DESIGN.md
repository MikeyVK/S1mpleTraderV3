<!-- filepath: docs/development/backend/dtos/EXECUTION_PLAN_DESIGN.md -->
# ExecutionPlan Design Document

**Status:** ✅ Implemented  
**Version:** 1.0  
**Last Updated:** 2025-12-01

---

## 1. Identity

| Aspect | Value |
|--------|-------|
| **DTO Name** | ExecutionPlan |
| **ID Prefix** | `EXP_` |
| **Layer** | Planning (TradePlanner output) |
| **File Path** | `backend/dtos/strategy/execution_plan.py` |
| **Status** | ✅ Implemented |

---

## 2. Contract

| Role | Component |
|------|-----------|
| **Producer** | ExecutionPlanner (4th TradePlanner) |
| **Consumer(s)** | ExecutionCommand, ExecutionWorker |
| **Trigger** | Entry + Size + Exit plans aggregated |

**Architectural Role (per PIPELINE_FLOW.md, TRADE_LIFECYCLE.md):**
- Phase 4 TradePlanner output (4th planner)
- Specifies HOW/WHEN (universal execution trade-offs)
- Connector-agnostic: translators convert to connector-specific specs

---

## 3. Fields

| Field | Type | Req | Producer | Consumer | Validation |
|-------|------|-----|----------|----------|------------|
| `plan_id` | `str` | ✅ | Auto-generated | ExecutionCommand, Journal | Pattern: `^EXP_\d{8}_\d{6}_[0-9a-z]{5,8}$` |
| `action` | `ExecutionAction` | ✅ | ExecutionPlanner | ExecutionWorker | Enum: EXECUTE_TRADE, CANCEL_ORDER, MODIFY_ORDER, CANCEL_GROUP |
| `execution_urgency` | `Decimal` | ❌ | ExecutionPlanner | Translator | [0.0-1.0], 0=patient, 1=urgent |
| `visibility_preference` | `Decimal` | ❌ | ExecutionPlanner | Translator | [0.0-1.0], 0=stealth, 1=visible |
| `max_slippage_pct` | `Decimal` | ❌ | ExecutionPlanner | ExecutionWorker | Hard price limit [0.0-1.0] |
| `must_complete_immediately` | `bool` | ❌ | ExecutionPlanner | ExecutionWorker | Force immediate execution |
| `max_execution_window_minutes` | `int \| None` | ❌ | ExecutionPlanner | ExecutionWorker | Time window for completion |
| `preferred_execution_style` | `str \| None` | ❌ | ExecutionPlanner | Translator | Hint: "TWAP", "VWAP", etc. |
| `chunk_count_hint` | `int \| None` | ❌ | ExecutionPlanner | Translator | Hint for number of chunks |
| `chunk_distribution` | `str \| None` | ❌ | ExecutionPlanner | Translator | Hint: "UNIFORM", "WEIGHTED" |
| `min_fill_ratio` | `Decimal \| None` | ❌ | ExecutionPlanner | ExecutionWorker | Min fill ratio to accept |

---

## 4. Enums

### ExecutionAction

```python
EXECUTE_TRADE = "EXECUTE_TRADE"    # Execute new trade (default)
CANCEL_ORDER = "CANCEL_ORDER"      # Cancel specific order
MODIFY_ORDER = "MODIFY_ORDER"      # Modify existing order
CANCEL_GROUP = "CANCEL_GROUP"      # Cancel entire execution group
```

---

## 5. Causality

| Aspect | Value |
|--------|-------|
| **Category** | Planning output (post-causality) |
| **Has causality field** | ❌ NO - Sub-planners don't track causality |
| **ID tracked in CausalityChain** | `execution_plan_id` added to ExecutionCommand |

---

## 6. Immutability

| Decision | Rationale |
|----------|-----------|
| **frozen** | `True` |
| **Why** | Planning output - immutable for audit trail. |

---

## 7. Examples

### High Urgency Market Order
```json
{
  "plan_id": "EXP_20251201_143450_pqr901",
  "action": "EXECUTE_TRADE",
  "execution_urgency": "0.95",
  "visibility_preference": "1.0",
  "max_slippage_pct": "0.0100",
  "must_complete_immediately": true,
  "max_execution_window_minutes": null,
  "preferred_execution_style": null,
  "chunk_count_hint": null,
  "chunk_distribution": null,
  "min_fill_ratio": "0.95"
}
```

### Patient TWAP Execution
```json
{
  "plan_id": "EXP_20251201_144000_stu234",
  "action": "EXECUTE_TRADE",
  "execution_urgency": "0.20",
  "visibility_preference": "0.30",
  "max_slippage_pct": "0.0030",
  "must_complete_immediately": false,
  "max_execution_window_minutes": 60,
  "preferred_execution_style": "TWAP",
  "chunk_count_hint": 12,
  "chunk_distribution": "UNIFORM",
  "min_fill_ratio": null
}
```

### Cancel Group
```json
{
  "plan_id": "EXP_20251201_150000_vwx567",
  "action": "CANCEL_GROUP",
  "execution_urgency": "1.0",
  "must_complete_immediately": true
}
```

---

## 8. Dependencies

- `backend/utils/id_generators.py` → `generate_execution_plan_id()`
- `pydantic.BaseModel`
- `decimal.Decimal`
- `enum.Enum`

---

## 9. Breaking Changes

None required. DTO follows architectural guidelines.

**Design Pattern - Constraints vs Hints:**
- **Constraints (MUST):** `max_slippage_pct`, `must_complete_immediately` - ExecutionWorker MUST respect
- **Hints (MAY):** `preferred_execution_style`, `chunk_count_hint` - Translator MAY interpret

**Translation Pattern:**
```
ExecutionPlan (universal) 
    → ExecutionTranslator 
    → ConnectorExecutionSpec (CEX/DEX/Backtest specific)
```

---

## 10. Verification Checklist

- [x] Follows lean DTO principles
- [x] No causality field (sub-planner)
- [x] Uses Decimal for trade-off values
- [x] Clear separation: constraints vs hints
- [x] Connector-agnostic design

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|--------|
| 1.0 | 2025-12-01 | AI Agent | Initial design document |
