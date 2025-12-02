<!-- filepath: docs/development/backend/dtos/FILL_DESIGN.md -->
# Fill Design Document

**Status:** ❌ Not Implemented  
**Version:** 1.0  
**Last Updated:** 2025-12-01

---

## 1. Identity

| Aspect | Value |
|--------|-------|
| **DTO Name** | Fill |
| **ID Prefix** | `FIL_` |
| **Layer** | State (Ledger-owned container) |
| **File Path** | `backend/dtos/state/fill.py` |
| **Status** | ❌ Not Implemented |

---

## 2. Contract

| Role | Component |
|------|-----------|
| **Producer** | ExchangeConnector (async reply flow) |
| **Owner** | StrategyLedger (single source of truth) |
| **Consumer(s)** | StrategyLedger, StrategyJournal, Quant Analysis |
| **Trigger** | Exchange reports fill on private websocket |

**Architectural Role (per TRADE_LIFECYCLE.md):**
- Level 4 container in hierarchy: TradePlan → ExecutionGroup → Order → **Fill**
- Represents **execution reality** (what actually happened)
- May differ from Order (partial fills, price improvement, slippage)
- Owned exclusively by StrategyLedger

**Key Insight:** Fill is REALITY. Order is INTENT. They may differ.

---

## 3. Fields

| Field | Type | Req | Producer | Consumer | Validation |
|-------|------|-----|----------|----------|------------|
| `fill_id` | `str` | ✅ | Auto-generated | Ledger, Journal | Pattern: `^FIL_\d{8}_\d{6}_[0-9a-f]{8}$` |
| `parent_order_id` | `str` | ✅ | System | Ledger | Pattern: `^ORD_...` |
| `connector_fill_id` | `str \| None` | ❌ | ExchangeConnector | Ledger | Exchange-assigned fill ID |
| `filled_quantity` | `Decimal` | ✅ | Connector | Ledger, Quant | > 0 |
| `fill_price` | `Decimal` | ✅ | Connector | Ledger, Quant | > 0 |
| `commission` | `Decimal \| None` | ❌ | Connector | Quant | >= 0 |
| `commission_asset` | `str \| None` | ❌ | Connector | Quant | Asset symbol (e.g., "BNB", "USDT") |
| `executed_at` | `datetime` | ✅ | Connector | Ledger, Journal | UTC - when exchange executed |

---

## 4. Causality

| Aspect | Value |
|--------|-------|
| **Category** | State container (Ledger-owned) |
| **Has causality field** | ❌ **NO** - Causality lives in StrategyJournal |
| **ID tracked in CausalityChain** | `fill_ids[]` array extended by ExecutionWorker |

**Per EXECUTION_FLOW.md Async Flow:**
```
ExchangeConnector (private websocket: fills)
    ↓
ExecutionWorker
    ├→ Generate FillID
    ├→ Register Fill container in Ledger
    └→ Add fill_id to CausalityChain
    ↓
StrategyJournalWriter
    └→ Write journal entry: causality + order_id + fill_id
```

---

## 5. Immutability

| Decision | Rationale |
|----------|-----------|
| **frozen** | `True` |
| **Why** | Immutable fact from exchange. Fills are never modified after creation. |

**Key difference from Order:** Order is mutable (status changes), Fill is immutable (historical fact).

---

## 6. Examples

### Market Order Fill
```json
{
  "fill_id": "FIL_20251201_150102_a1b2c3d4",
  "parent_order_id": "ORD_20251201_150100_b2c3d4e5",
  "connector_fill_id": "binance_fill_987654321",
  "filled_quantity": "2.0",
  "fill_price": "3450.25",
  "commission": "0.003",
  "commission_asset": "BNB",
  "executed_at": "2025-12-01T15:01:02.456Z"
}
```

### Partial Fill (first of many)
```json
{
  "fill_id": "FIL_20251201_151000_c3d4e5f6",
  "parent_order_id": "ORD_20251201_150955_def123",
  "connector_fill_id": "binance_fill_111222333",
  "filled_quantity": "0.2",
  "fill_price": "95000.50",
  "commission": "0.00004",
  "commission_asset": "BTC",
  "executed_at": "2025-12-01T15:10:00.123Z"
}
```

### Partial Fill (second of many - same order)
```json
{
  "fill_id": "FIL_20251201_151030_d4e5f6a7",
  "parent_order_id": "ORD_20251201_150955_def123",
  "connector_fill_id": "binance_fill_111222334",
  "filled_quantity": "0.3",
  "fill_price": "95001.00",
  "commission": "0.00006",
  "commission_asset": "BTC",
  "executed_at": "2025-12-01T15:10:30.789Z"
}
```

---

## 7. Dependencies

- `backend/utils/id_generators.py` → `generate_fill_id()` (NEW - to be added)
- `pydantic.BaseModel`
- `decimal.Decimal`
- `datetime.datetime`

---

## 8. Implementation Checklist

### Prerequisites
- [ ] Implement Order DTO first (Fill references Order)
- [ ] Add `generate_fill_id()` to `backend/utils/id_generators.py`

### TDD Steps

#### Phase 1: Write Tests (RED)
```python
# tests/unit/dtos/state/test_fill.py

class TestFillCreation:
    def test_create_with_required_fields(self) -> None:
        """Should create Fill with required fields."""
        fill = Fill(
            parent_order_id="ORD_20251201_150100_b2c3d4e5",
            filled_quantity=Decimal("2.0"),
            fill_price=Decimal("3450.25"),
            executed_at=datetime.now(timezone.utc)
        )
        assert fill.fill_id.startswith("FIL_")

class TestFillIdValidation:
    def test_auto_generates_id_with_correct_prefix(self) -> None:
        """Should auto-generate ID with FIL_ prefix."""
        pass

class TestFillImmutability:
    def test_cannot_modify_after_creation(self) -> None:
        """Should raise error when modifying frozen instance."""
        fill = Fill(...)
        with pytest.raises(ValidationError):
            fill.fill_price = Decimal("9999.99")
```

#### Phase 2: Implement (GREEN)
- Create `backend/dtos/state/fill.py`
- Implement minimal DTO

#### Phase 3: Refactor
- Add docstrings
- Add model_config with frozen=True

---

## 9. Lean Design Notes

**NOT included (per lean principles):**
- ❌ `causality` - Separate concern (StrategyJournal)
- ❌ `symbol` - Available via parent_order_id lookup
- ❌ `side` - Available via parent_order_id lookup
- ❌ `order_type` - Available via parent_order_id lookup
- ❌ `slippage` - Computed on-demand (fill_price vs order_price)

**Why lean?**
- Fill = immutable execution fact
- Minimal duplication - lookup parent for context
- Computations (slippage, average price) done at query time

---

## 10. Quant Analysis Patterns

### Average Fill Price (for Order)
```python
def get_average_fill_price(order_id: str) -> Decimal:
    fills = ledger.get_fills_for_order(order_id)
    total_value = sum(f.filled_quantity * f.fill_price for f in fills)
    total_qty = sum(f.filled_quantity for f in fills)
    return total_value / total_qty if total_qty > 0 else Decimal("0")
```

### Total Commission (for Order)
```python
def get_total_commission(order_id: str) -> dict[str, Decimal]:
    fills = ledger.get_fills_for_order(order_id)
    commissions: dict[str, Decimal] = {}
    for f in fills:
        if f.commission and f.commission_asset:
            commissions[f.commission_asset] = commissions.get(
                f.commission_asset, Decimal("0")
            ) + f.commission
    return commissions
```

### Slippage Analysis
```python
def calculate_slippage(order_id: str) -> Decimal | None:
    order = ledger.get_order(order_id)
    if order.price is None:  # Market order
        return None
    avg_fill = get_average_fill_price(order_id)
    return (avg_fill - order.price) / order.price
```

---

## 11. Verification Checklist

### Design Document
- [x] All sections completed
- [x] Reviewed against TRADE_LIFECYCLE.md
- [x] Reviewed against EXECUTION_FLOW.md
- [x] Lean design rationale documented
- [x] Quant patterns documented

### Implementation (future)
- [ ] Order DTO implemented first
- [ ] File created: `backend/dtos/state/fill.py`
- [ ] ID generator added
- [ ] Tests written and passing
- [ ] Integration tested

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|--------|
| 1.0 | 2025-12-01 | AI Agent | Initial design document |
