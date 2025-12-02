<!-- filepath: docs/development/backend/dtos/EXECUTION_GROUP_DESIGN.md -->
# ExecutionGroup Design Document

**Status:** Refactor Required  
**Version:** 1.0  
**Last Updated:** 2025-12-01

---

## 1. Identity

| Aspect | Value |
|--------|-------|
| **DTO Name** | ExecutionGroup |
| **ID Prefix** | `EXG_` |
| **Layer** | State (Ledger-owned container) |
| **File Path** | `backend/dtos/execution/execution_group.py` |
| **Status** | ⚠️ Needs Refactor |

---

## 2. Contract

| Role | Component |
|------|-----------|
| **Producer** | ExecutionWorker (creates on-demand) |
| **Owner** | StrategyLedger (single source of truth) |
| **Consumer(s)** | ExecutionWorker, StrategyJournal, Quant Analysis |
| **Trigger** | Order registration requires a parent group |

**Architectural Role (per TRADE_LIFECYCLE.md):**
- Level 2 container in hierarchy: TradePlan → **ExecutionGroup** → Order → Fill
- Groups multiple Orders for advanced execution strategies (TWAP, Iceberg, etc.)
- Created on-demand by StrategyLedger when Order needs a parent
- Owned exclusively by StrategyLedger

---

## 3. Fields

| Field | Type | Req | Producer | Consumer | Validation |
|-------|------|-----|----------|----------|------------|
| `group_id` | `str` | ✅ | Auto-generated | Ledger, Journal | Pattern: `^EXG_\d{8}_\d{6}_[0-9a-z]{5,8}$` |
| `parent_plan_id` | `str` | ✅ | ExecutionWorker | Ledger | Pattern: `^TPL_...` (parent TradePlan) |
| `execution_strategy` | `ExecutionStrategyType` | ✅ | ExecutionWorker | ExecutionWorker | Enum (see below) |
| `order_ids` | `list[str]` | ✅ | ExecutionWorker | Ledger | Unique values, ORD_ prefix |
| `status` | `GroupStatus` | ✅ | ExecutionWorker | Ledger, Journal | Enum (see below) |
| `created_at` | `datetime` | ✅ | ExecutionWorker | Ledger, Journal | UTC |
| `updated_at` | `datetime` | ✅ | ExecutionWorker | Ledger | UTC |
| `target_quantity` | `Decimal \| None` | ❌ | ExecutionWorker | ExecutionWorker | Planned total quantity |
| `filled_quantity` | `Decimal \| None` | ❌ | ExchangeConnector | Ledger, Quant | Actual filled quantity |
| `cancelled_at` | `datetime \| None` | ❌ | ExecutionWorker | Ledger | When group was cancelled |
| `completed_at` | `datetime \| None` | ❌ | ExecutionWorker | Ledger | When group completed |

---

## 4. Enums

### ExecutionStrategyType (REFACTOR NEEDED)

**Current enum values:**
```python
SINGLE = "SINGLE"      # Single order (no grouping needed)
TWAP = "TWAP"          # Time-Weighted Average Price
VWAP = "VWAP"          # Volume-Weighted Average Price
ICEBERG = "ICEBERG"    # Iceberg order (visible/hidden pairs)
DCA = "DCA"            # ⚠️ REMOVE - Planning concept, not execution
LAYERED = "LAYERED"    # Layered limit orders
POV = "POV"            # Percentage of Volume
```

**Issue:** `DCA` is a **Planning concept** (Dollar-Cost Averaging), not an **Execution strategy**.
Per WORKER_TAXONOMY.md, ExecutionWorker handles: TWAP, Iceberg, MarketMaker.
DCA belongs to StrategyPlanner level (scheduled DCA strategy, not execution algorithm).

**Proposed values (after refactor):**
```python
SINGLE = "SINGLE"
TWAP = "TWAP"
VWAP = "VWAP"
ICEBERG = "ICEBERG"
LAYERED = "LAYERED"
POV = "POV"
MARKET_MAKER = "MARKET_MAKER"  # Optional: if needed
```

### GroupStatus

```python
PENDING = "PENDING"       # Created, no orders yet
ACTIVE = "ACTIVE"         # Orders being executed
COMPLETED = "COMPLETED"   # All orders filled/complete
CANCELLED = "CANCELLED"   # Group cancelled
FAILED = "FAILED"         # Execution failed (error state)
PARTIAL = "PARTIAL"       # Some orders filled, group stopped
```

---

## 5. Causality

| Aspect | Value |
|--------|-------|
| **Category** | State container (Ledger-owned) |
| **Has causality field** | ❌ **NO** - Causality lives in StrategyJournal |
| **Correlation** | Via `group_id` lookup in Journal |

**Per EXECUTION_FLOW.md SRP Separation:**
- StrategyLedger: Order/fill/trade reality ONLY (NO causality storage)
- StrategyJournal: Causality + correlates order_ids + fill_ids
- Quant Analysis: Cross-query Ledger ↔ Journal via order_id/fill_id

---

## 6. Immutability

| Decision | Rationale |
|----------|-----------|
| **frozen** | `False` |
| **Why** | Mutable tracking entity. Status, timestamps, filled_quantity evolve during execution. |

**Immutable identifiers:** `group_id`, `parent_plan_id` never change after creation.

---

## 7. Examples

### TWAP Group - Active
```json
{
  "group_id": "EXG_20251201_143022_a8f3c",
  "parent_plan_id": "TPL_20251201_143000_b7c4d",
  "execution_strategy": "TWAP",
  "order_ids": [
    "ORD_20251201_143025_001",
    "ORD_20251201_143325_002",
    "ORD_20251201_143625_003"
  ],
  "status": "ACTIVE",
  "created_at": "2025-12-01T14:30:22Z",
  "updated_at": "2025-12-01T14:36:30Z",
  "target_quantity": "1.0",
  "filled_quantity": "0.4",
  "cancelled_at": null,
  "completed_at": null
}
```

### Single Order Group - Completed
```json
{
  "group_id": "EXG_20251201_150015_b9d2e",
  "parent_plan_id": "TPL_20251201_150000_c3f1g",
  "execution_strategy": "SINGLE",
  "order_ids": ["ORD_20251201_150018_001"],
  "status": "COMPLETED",
  "created_at": "2025-12-01T15:00:15Z",
  "updated_at": "2025-12-01T15:00:45Z",
  "target_quantity": "0.5",
  "filled_quantity": "0.5",
  "cancelled_at": null,
  "completed_at": "2025-12-01T15:00:45Z"
}
```

---

## 8. Dependencies

- `backend/utils/id_generators.py` → `generate_execution_group_id()`
- `pydantic.BaseModel`
- `decimal.Decimal`
- `datetime.datetime`
- `enum.Enum`

---

## 9. Breaking Changes Required

| Current | New | Impact |
|---------|-----|--------|
| `ExecutionStrategyType.DCA` | **REMOVE** | Remove enum value. Update any usages. |
| `metadata: Dict[str, Any]` | **REMOVE or TYPE** | Untyped dict violates lean principle. See analysis below. |
| `parent_directive_id` | `parent_plan_id` | Align with TradePlan terminology if not already. |

### Metadata Field Analysis

**Current state:** `metadata: Dict[str, Any]` for "strategy-specific parameters"

**Issue:** Untyped dict = undefined contract, violates lean DTO principle.

**Options:**
1. **REMOVE** if no concrete consumer exists
2. **TYPE** with specific fields if needed (e.g., `chunk_size`, `interval_seconds` for TWAP)

**Recommendation:** Analyze current usage. If only used for TWAP/ICEBERG params, create typed fields:
```python
# For TWAP
chunk_count: int | None = None
interval_seconds: int | None = None

# For ICEBERG
visible_quantity: Decimal | None = None
hidden_quantity: Decimal | None = None
```

### Migration Checklist

- [ ] Remove `DCA` from `ExecutionStrategyType` enum
- [ ] Analyze `metadata` usage and either remove or type
- [ ] Update all tests
- [ ] Update ExecutionWorker implementations

---

## 10. Verification Checklist

### Design Document
- [x] All 8 sections completed
- [x] Reviewed against TRADE_LIFECYCLE.md
- [x] Reviewed against WORKER_TAXONOMY.md
- [x] Breaking changes documented

### Implementation (post-refactor)
- [ ] `DCA` removed from enum
- [ ] `metadata` addressed (removed or typed)
- [ ] Follows CODE_STYLE.md structure
- [ ] model_config correct (frozen=False)

### Tests (post-refactor)
- [ ] Test file updated
- [ ] All tests pass

### Quality Gates
- [ ] `pytest tests/unit/dtos/execution/test_execution_group.py` - ALL PASS
- [ ] `pyright backend/dtos/execution/execution_group.py` - No errors

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|--------|
| 1.0 | 2025-12-01 | AI Agent | Initial design document |
