<!-- filepath: docs/development/backend/dtos/EXIT_PLAN_DESIGN.md -->
# ExitPlan Design Document

**Status:** ✅ Implemented (Lean)  
**Version:** 1.0  
**Last Updated:** 2025-12-01

---

## 1. Identity

| Aspect | Value |
|--------|-------|
| **DTO Name** | ExitPlan |
| **ID Prefix** | `EXT_` |
| **Layer** | Planning (TradePlanner output) |
| **File Path** | `backend/dtos/strategy/exit_plan.py` |
| **Status** | ✅ Implemented |

---

## 2. Contract

| Role | Component |
|------|-----------|
| **Producer** | ExitPlanner (planning worker) |
| **Consumer(s)** | ExecutionPlanner (aggregation), ExecutionWorker |
| **Trigger** | StrategyDirective received with exit_directive hints |

**Architectural Role (per PIPELINE_FLOW.md):**
- Phase 4 TradePlanner output
- Specifies WHERE OUT (static exit price levels)
- Pure execution parameters - no dynamic behavior

---

## 3. Fields

| Field | Type | Req | Producer | Consumer | Validation |
|-------|------|-----|----------|----------|------------|
| `plan_id` | `str` | ✅ | Auto-generated | ExecutionPlanner, Journal | Pattern: `^EXT_\d{8}_\d{6}_[0-9a-f]{8}$` |
| `stop_loss_price` | `Decimal` | ✅ | ExitPlanner | ExecutionWorker | SL price level, > 0 |
| `take_profit_price` | `Decimal \| None` | ❌ | ExitPlanner | ExecutionWorker | TP price level, > 0 |

---

## 4. Causality

| Aspect | Value |
|--------|-------|
| **Category** | Planning output (post-causality) |
| **Has causality field** | ❌ NO - Sub-planners don't track causality |
| **ID tracked in CausalityChain** | `exit_plan_id` added by ExecutionPlanner |

**Design Note:**
ExitPlan is a static snapshot of exit levels. Dynamic behavior (trailing stops, breakeven adjustments) is handled by PositionMonitor, not this DTO.

---

## 5. Immutability

| Decision | Rationale |
|----------|-----------|
| **frozen** | `True` (implicit via lean design) |
| **Why** | Pure planning output - never modified after creation. |

---

## 6. Examples

### SL and TP
```json
{
  "plan_id": "EXT_20251201_143400_mno678",
  "stop_loss_price": "95000.00",
  "take_profit_price": "105000.00"
}
```

### SL Only (Let Winners Run)
```json
{
  "plan_id": "EXT_20251201_143500_pqr901",
  "stop_loss_price": "94000.00",
  "take_profit_price": null
}
```

---

## 7. Dependencies

- `backend/utils/id_generators.py` → `generate_exit_plan_id()`
- `pydantic.BaseModel`
- `decimal.Decimal`

---

## 8. Breaking Changes

None required. DTO follows lean spec and architectural guidelines.

**Previous Refactor (completed):**
- Removed: Trailing stop logic, breakeven adjustments
- Removed: Metadata, timestamps, causality
- Kept: Static price levels only

---

## 9. Verification Checklist

- [x] Follows lean DTO principles
- [x] No causality field (sub-planner)
- [x] Uses Decimal for price fields
- [x] SL is required, TP is optional
- [x] No dynamic behavior logic

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|--------|
| 1.0 | 2025-12-01 | AI Agent | Initial design document |
