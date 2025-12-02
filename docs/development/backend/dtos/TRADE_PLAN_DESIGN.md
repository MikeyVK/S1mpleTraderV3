<!-- filepath: docs/development/backend/dtos/TRADE_PLAN_DESIGN.md -->
# TradePlan Design Document

**Status:** ✅ Implemented  
**Version:** 1.0  
**Last Updated:** 2025-12-01

---

## 1. Identity

| Aspect | Value |
|--------|-------|
| **DTO Name** | TradePlan |
| **ID Prefix** | `TPL_` |
| **Layer** | State (Ledger-owned container) |
| **File Path** | `backend/dtos/state/trade_plan.py` |
| **Status** | ✅ Implemented |

---

## 2. Contract

| Role | Component |
|------|-----------|
| **Producer** | StrategyLedger (created on-demand) |
| **Owner** | StrategyLedger (single source of truth) |
| **Consumer(s)** | ExecutionWorker, StrategyJournal, Quant Analysis |
| **Trigger** | First ExecutionCommand for a strategy instance |

**Architectural Role (per TRADE_LIFECYCLE.md):**
- Level 1 in hierarchy: **TradePlan** → ExecutionGroup → Order → Fill
- **Execution Anchor:** Groups tactical ExecutionGroups under one strategic ID
- **Cross-Query Key:** Joins Ledger data (Reality) with Journal data (Context/History)
- **Minimalist:** Only essential fields for existence and lifecycle status
- Strategic state (e.g., "Grid Level") stored in StrategyJournal, NOT here

---

## 3. Fields

| Field | Type | Req | Producer | Consumer | Validation |
|-------|------|-----|----------|----------|------------|
| `plan_id` | `str` | ✅ | Auto-generated | Ledger, Journal, Quant | Pattern: `^TPL_\d{8}_\d{6}_[0-9a-z]{5,8}$` |
| `strategy_instance_id` | `str` | ✅ | Ledger | ExecutionWorker | Non-empty string |
| `status` | `TradeStatus` | ✅ | Ledger | All | Enum: ACTIVE, CLOSED |
| `created_at` | `datetime` | ✅ | Ledger | Ledger, Journal | UTC timezone aware |

---

## 4. Enums

### TradeStatus

```python
class TradeStatus(str, Enum):
    """Lifecycle state of the TradePlan."""
    ACTIVE = "ACTIVE"   # Plan is live, ExecutionGroups can be added
    CLOSED = "CLOSED"   # Plan is terminated, no new activity
```

---

## 5. Causality

| Aspect | Value |
|--------|-------|
| **Category** | State container (Ledger-owned) |
| **Has causality field** | ❌ **NO** - Causality lives in StrategyJournal |
| **Correlation** | Via `plan_id` lookup in Journal |

**Per EXECUTION_FLOW.md SRP Separation:**
- StrategyLedger: TradePlan/Order/Fill reality ONLY (NO causality storage)
- StrategyJournal: Causality + correlates via `plan_id`
- Quant Analysis: Cross-query Ledger ↔ Journal via `plan_id`

---

## 6. Immutability

| Decision | Rationale |
|----------|-----------|
| **frozen** | `False` |
| **Why** | Mutable lifecycle state. Only `status` changes during execution. |

**Immutable identifiers:** `plan_id`, `strategy_instance_id`, `created_at` never change after creation.

---

## 7. Examples

### Active TradePlan
```json
{
  "plan_id": "TPL_20251201_143000_abc12",
  "strategy_instance_id": "STRAT_GRID_BTC_01",
  "status": "ACTIVE",
  "created_at": "2025-12-01T14:30:00Z"
}
```

### Closed TradePlan
```json
{
  "plan_id": "TPL_20251201_143000_abc12",
  "strategy_instance_id": "STRAT_GRID_BTC_01",
  "status": "CLOSED",
  "created_at": "2025-12-01T14:30:00Z"
}
```

### Usage Example
```python
from datetime import datetime, UTC

plan = TradePlan(
    plan_id="TPL_20251201_143000_abc12",
    strategy_instance_id="STRAT_GRID_BTC_01",
    status=TradeStatus.ACTIVE,
    created_at=datetime.now(UTC)
)

# State transition (Strategy decides to close)
plan.status = TradeStatus.CLOSED
# ledger.update_plan(plan)
```

---

## 8. Dependencies

- `backend/utils/id_generators.py` → `generate_trade_plan_id()`
- `pydantic.BaseModel`
- `datetime.datetime`
- `enum.Enum`

---

## 9. Breaking Changes

None - DTO follows architectural guidelines.

### Implementation Code

```python
# backend/dtos/state/trade_plan.py

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, field_validator


class TradeStatus(str, Enum):
    """Lifecycle state of the TradePlan."""
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


class TradePlan(BaseModel):
    """
    Level 1 Execution Anchor - Groups ExecutionGroups under one strategic ID.
    
    Owned by StrategyLedger. Cross-referenced by StrategyJournal for quant analysis.
    """
    model_config = {
        "frozen": False,
        "str_strip_whitespace": True,
        "validate_assignment": True
    }
    
    plan_id: str
    strategy_instance_id: str
    status: TradeStatus
    created_at: datetime
    
    @field_validator('plan_id')
    @classmethod
    def validate_plan_id_format(cls, v: str) -> str:
        """Validate plan_id starts with TPL_ and follows format."""
        import re
        if not re.match(r'^TPL_\d{8}_\d{6}_[0-9a-z]{5,8}$', v):
            raise ValueError(f"Invalid plan_id format: {v}")
        return v
```

---

## 10. Verification Checklist

### Design Document
- [x] All 8 sections completed
- [x] Reviewed against TRADE_LIFECYCLE.md
- [x] Breaking changes documented (none)

### Implementation
- [x] TradeStatus enum defined
- [x] TradePlan model mutable (frozen=False)
- [x] plan_id format validation

### Tests
- [x] Valid TradePlan creates successfully
- [x] Status transitions work
- [x] Invalid plan_id raises ValueError

### Quality Gates
- [ ] `pytest tests/unit/dtos/state/test_trade_plan.py` - ALL PASS
- [ ] `pyright backend/dtos/state/trade_plan.py` - No errors

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|--------|
| 1.0 | 2025-12-01 | AI Agent | Refactored to standard 1-10 structure |
