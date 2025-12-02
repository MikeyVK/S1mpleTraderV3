<!-- filepath: docs/development/backend/dtos/ENTRY_PLAN_DESIGN.md -->
# EntryPlan Design Document

**Status:** ✅ Implemented (Lean)  
**Version:** 1.0  
**Last Updated:** 2025-12-01

---

## 1. Identity

| Aspect | Value |
|--------|-------|
| **DTO Name** | EntryPlan |
| **ID Prefix** | `ENT_` |
| **Layer** | Planning (TradePlanner output) |
| **File Path** | `backend/dtos/strategy/entry_plan.py` |
| **Status** | ✅ Implemented |

---

## 2. Contract

| Role | Component |
|------|-----------|
| **Producer** | EntryPlanner (planning worker) |
| **Consumer(s)** | ExecutionPlanner (aggregation), ExecutionWorker |
| **Trigger** | StrategyDirective received with entry_directive hints |

**Architectural Role (per PIPELINE_FLOW.md):**
- Phase 4 TradePlanner output
- Specifies WHAT/WHERE to enter (not HOW/WHEN)
- Pure execution parameters without timing/routing

---

## 3. Fields

| Field | Type | Req | Producer | Consumer | Validation |
|-------|------|-----|----------|----------|------------|
| `plan_id` | `str` | ✅ | Auto-generated | ExecutionPlanner, Journal | Pattern: `^ENT_\d{8}_\d{6}_[0-9a-f]{8}$` |
| `symbol` | `str` | ✅ | EntryPlanner | ExecutionWorker | Trading pair (e.g., `BTC_USDT`) |
| `direction` | `Literal["BUY", "SELL"]` | ✅ | EntryPlanner | ExecutionWorker | Execution direction |
| `order_type` | `Literal["MARKET", "LIMIT", "STOP_LIMIT"]` | ✅ | EntryPlanner | ExecutionWorker | Order execution type |
| `limit_price` | `Decimal \| None` | ❌ | EntryPlanner | ExecutionWorker | For LIMIT orders |
| `stop_price` | `Decimal \| None` | ❌ | EntryPlanner | ExecutionWorker | For STOP_LIMIT orders |

---

## 4. Causality

| Aspect | Value |
|--------|-------|
| **Category** | Planning output (post-causality) |
| **Has causality field** | ❌ NO - Sub-planners don't track causality |
| **ID tracked in CausalityChain** | `entry_plan_id` added by ExecutionPlanner |

**Design Note:** 
Sub-planners receive StrategyDirective (has causality). ExecutionPlanner extracts causality and adds plan IDs to create ExecutionCommand with complete chain.

---

## 5. Immutability

| Decision | Rationale |
|----------|-----------|
| **frozen** | `True` (implicit via lean design) |
| **Why** | Pure planning output - never modified after creation. |

---

## 6. Examples

### Limit Order Entry
```json
{
  "plan_id": "ENT_20251201_143300_ghi012",
  "symbol": "BTC_USDT",
  "direction": "BUY",
  "order_type": "LIMIT",
  "limit_price": "95500.00",
  "stop_price": null
}
```

### Market Order Entry
```json
{
  "plan_id": "ENT_20251201_143400_jkl345",
  "symbol": "ETH_USDT",
  "direction": "SELL",
  "order_type": "MARKET",
  "limit_price": null,
  "stop_price": null
}
```

---

## 7. Dependencies

- `backend/utils/id_generators.py` → `generate_entry_plan_id()`
- `pydantic.BaseModel`
- `decimal.Decimal`

---

## 8. Breaking Changes

None required. DTO follows lean spec and architectural guidelines.

**Previous Refactor (completed):**
- Removed: `created_at`, `planner_id`, `timing`, `reference_price`, `max_slippage_pct`
- Removed: `valid_until`, `planner_metadata`, `rationale`, `causality`
- Kept: Pure entry specification only

---

## 9. Verification Checklist

- [x] Follows lean DTO principles
- [x] No causality field (sub-planner)
- [x] Uses Decimal for price fields
- [x] Direction uses execution convention ("BUY"/"SELL")
- [x] No unnecessary metadata

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|--------|
| 1.0 | 2025-12-01 | AI Agent | Initial design document |
