<!-- filepath: docs/development/backend/dtos/SIZE_PLAN_DESIGN.md -->
# SizePlan Design Document

**Status:** ✅ Implemented (Lean)  
**Version:** 1.0  
**Last Updated:** 2025-12-01

---

## 1. Identity

| Aspect | Value |
|--------|-------|
| **DTO Name** | SizePlan |
| **ID Prefix** | `SIZ_` |
| **Layer** | Planning (TradePlanner output) |
| **File Path** | `backend/dtos/strategy/size_plan.py` |
| **Status** | ✅ Implemented |

---

## 2. Contract

| Role | Component |
|------|-----------|
| **Producer** | SizePlanner (planning worker) |
| **Consumer(s)** | ExecutionPlanner (aggregation), ExecutionWorker |
| **Trigger** | StrategyDirective received with size_directive hints |

**Architectural Role (per PIPELINE_FLOW.md):**
- Phase 4 TradePlanner output
- Specifies HOW MUCH (absolute sizing only)
- Pure execution parameters - no account percentages

---

## 3. Fields

| Field | Type | Req | Producer | Consumer | Validation |
|-------|------|-----|----------|----------|------------|
| `plan_id` | `str` | ✅ | Auto-generated | ExecutionPlanner, Journal | Pattern: `^SIZ_\d{8}_\d{6}_[0-9a-f]{8}$` |
| `position_size` | `Decimal` | ✅ | SizePlanner | ExecutionWorker | Base asset quantity (e.g., 0.5 BTC), > 0 |
| `position_value` | `Decimal` | ✅ | SizePlanner | ExecutionWorker | Quote asset value (e.g., 50000 USDT), > 0 |
| `risk_amount` | `Decimal` | ✅ | SizePlanner | ExecutionWorker | Absolute risk in quote (e.g., 1000 USDT), > 0 |
| `leverage` | `Decimal` | ❌ | SizePlanner | ExecutionWorker | Leverage multiplier, default 1.0, >= 1.0 |

---

## 4. Causality

| Aspect | Value |
|--------|-------|
| **Category** | Planning output (post-causality) |
| **Has causality field** | ❌ NO - Sub-planners don't track causality |
| **ID tracked in CausalityChain** | `size_plan_id` added by ExecutionPlanner |

**Design Note:**
SizePlanner workers use account_risk_pct/max_position_value as INPUTS to calculate these OUTPUTS. The DTO contains only the calculated absolute values.

---

## 5. Immutability

| Decision | Rationale |
|----------|-----------|
| **frozen** | `True` (implicit via lean design) |
| **Why** | Pure planning output - never modified after creation. |

---

## 6. Examples

### Standard Position (No Leverage)
```json
{
  "plan_id": "SIZ_20251201_143350_jkl345",
  "position_size": "0.5",
  "position_value": "50000.00",
  "risk_amount": "1000.00",
  "leverage": "1.0"
}
```

### Leveraged Position
```json
{
  "plan_id": "SIZ_20251201_143400_mno678",
  "position_size": "1.0",
  "position_value": "100000.00",
  "risk_amount": "2000.00",
  "leverage": "2.0"
}
```

---

## 7. Dependencies

- `backend/utils/id_generators.py` → `generate_size_plan_id()`
- `pydantic.BaseModel`
- `decimal.Decimal`

---

## 8. Breaking Changes

None required. DTO follows lean spec and architectural guidelines.

**Previous Refactor (completed):**
- Removed: `account_risk_pct` (input constraint, not output)
- Removed: `max_position_value` (planner constraint, not output)
- Kept: Only absolute sizing values

---

## 9. Verification Checklist

- [x] Follows lean DTO principles
- [x] No causality field (sub-planner)
- [x] Uses Decimal for all financial fields
- [x] No percentage fields (those are inputs, not outputs)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|--------|
| 1.0 | 2025-12-01 | AI Agent | Initial design document |
- [x] All required fields have `gt=0` validation
