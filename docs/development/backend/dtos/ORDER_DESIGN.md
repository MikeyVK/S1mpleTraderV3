<!-- filepath: docs/development/backend/dtos/ORDER_DESIGN.md -->
# Order Design Document

**Status:** ❌ Not Implemented  
**Version:** 1.0  
**Last Updated:** 2025-12-01

---

## 1. Identity

| Aspect | Value |
|--------|-------|
| **DTO Name** | Order |
| **ID Prefix** | `ORD_` |
| **Layer** | State (Ledger-owned container) |
| **File Path** | `backend/dtos/state/order.py` |
| **Status** | ❌ Not Implemented |

---

## 2. Contract

| Role | Component |
|------|-----------|
| **Producer** | ExecutionWorker |
| **Owner** | StrategyLedger (single source of truth) |
| **Consumer(s)** | StrategyLedger, StrategyJournal, ExchangeConnector |
| **Trigger** | ExecutionWorker places order via IExecutionConnector |

**Architectural Role (per TRADE_LIFECYCLE.md):**
- Level 3 container in hierarchy: TradePlan → ExecutionGroup → **Order** → Fill
- Represents **exchange intent** (what we want to happen)
- May differ from Fill (execution reality) - partial fills, rejections
- Owned exclusively by StrategyLedger

---

## 3. Fields

| Field | Type | Req | Producer | Consumer | Validation |
|-------|------|-----|----------|----------|------------|
| `order_id` | `str` | ✅ | Auto-generated | Ledger, Journal | Pattern: `^ORD_\d{8}_\d{6}_[0-9a-f]{8}$` |
| `parent_group_id` | `str` | ✅ | ExecutionWorker | Ledger | Pattern: `^EXG_...` |
| `connector_order_id` | `str \| None` | ❌ | ExchangeConnector | Ledger | Exchange-assigned ID |
| `symbol` | `str` | ✅ | From EntryPlan | Connector | Pattern: `^[A-Z]+_[A-Z]+$` |
| `side` | `Literal["BUY", "SELL"]` | ✅ | From EntryPlan | Connector | Execution direction |
| `order_type` | `OrderType` | ✅ | From EntryPlan | Connector | MARKET, LIMIT, STOP_LIMIT |
| `quantity` | `Decimal` | ✅ | From SizePlan | Connector, Ledger | > 0 |
| `price` | `Decimal \| None` | ❌ | From EntryPlan | Connector | For LIMIT orders |
| `stop_price` | `Decimal \| None` | ❌ | From EntryPlan | Connector | For STOP_LIMIT orders |
| `status` | `OrderStatus` | ✅ | Connector updates | Ledger | See enum below |
| `created_at` | `datetime` | ✅ | ExecutionWorker | Journal | UTC |
| `updated_at` | `datetime` | ✅ | Connector updates | Ledger | UTC |

---

## 4. Enums

### OrderType

```python
class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LIMIT = "STOP_LIMIT"
```

### OrderStatus

```python
class OrderStatus(str, Enum):
    PENDING = "PENDING"       # Created, not yet sent to exchange
    OPEN = "OPEN"             # Sent to exchange, awaiting fill
    PARTIALLY_FILLED = "PARTIALLY_FILLED"  # Partial execution
    FILLED = "FILLED"         # Completely filled
    CANCELLED = "CANCELLED"   # Cancelled by user/system
    REJECTED = "REJECTED"     # Rejected by exchange
    EXPIRED = "EXPIRED"       # Time-in-force expired
```

---

## 5. Causality

| Aspect | Value |
|--------|-------|
| **Category** | State container (Ledger-owned) |
| **Has causality field** | ❌ **NO** - Causality lives in StrategyJournal |
| **ID tracked in CausalityChain** | `order_ids[]` array extended by ExecutionWorker |

**Per EXECUTION_FLOW.md SRP Separation:**
- Order DTO = exchange intent/reality (StrategyLedger)
- Causality = decision chain (StrategyJournal)
- Correlated via `order_id` lookup

---

## 6. Immutability

| Decision | Rationale |
|----------|-----------|
| **frozen** | `False` |
| **Why** | Mutable tracking entity. Status, connector_order_id, updated_at evolve. |

**Immutable identifiers:** `order_id`, `parent_group_id` never change after creation.

---

## 7. Examples

### New Limit Order
```json
{
  "order_id": "ORD_20251201_150000_a1b2c3d4",
  "parent_group_id": "EXG_20251201_145955_xyz789",
  "connector_order_id": null,
  "symbol": "BTC_USDT",
  "side": "BUY",
  "order_type": "LIMIT",
  "quantity": "0.5",
  "price": "95000.00",
  "stop_price": null,
  "status": "PENDING",
  "created_at": "2025-12-01T15:00:00Z",
  "updated_at": "2025-12-01T15:00:00Z"
}
```

### Filled Market Order
```json
{
  "order_id": "ORD_20251201_150100_b2c3d4e5",
  "parent_group_id": "EXG_20251201_150055_abc123",
  "connector_order_id": "binance_order_12345678",
  "symbol": "ETH_USDT",
  "side": "SELL",
  "order_type": "MARKET",
  "quantity": "2.0",
  "price": null,
  "stop_price": null,
  "status": "FILLED",
  "created_at": "2025-12-01T15:01:00Z",
  "updated_at": "2025-12-01T15:01:02Z"
}
```

---

## 8. Dependencies

- `backend/utils/id_generators.py` → `generate_order_id()` (NEW - to be added)
- `backend/core/enums.py` → `OrderType`, `OrderStatus` (NEW - to be added)
- `pydantic.BaseModel`
- `decimal.Decimal`
- `datetime.datetime`

---

## 9. Implementation Checklist

### Prerequisites
- [ ] Add `generate_order_id()` to `backend/utils/id_generators.py`
- [ ] Add `OrderType`, `OrderStatus` enums to `backend/core/enums.py`

### TDD Steps

#### Phase 1: Write Tests (RED)
```python
# tests/unit/dtos/state/test_order.py

class TestOrderCreation:
    def test_create_with_required_fields(self) -> None:
        """Should create Order with required fields."""
        order = Order(
            parent_group_id="EXG_20251201_145955_xyz789",
            symbol="BTC_USDT",
            side="BUY",
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.5"),
            status=OrderStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        assert order.order_id.startswith("ORD_")

class TestOrderIdValidation:
    def test_auto_generates_id_with_correct_prefix(self) -> None:
        """Should auto-generate ID with ORD_ prefix."""
        pass

class TestOrderMutability:
    def test_can_update_status(self) -> None:
        """Should allow status updates (mutable)."""
        order = Order(...)
        order.status = OrderStatus.FILLED
        assert order.status == OrderStatus.FILLED
```

#### Phase 2: Implement (GREEN)
- Create `backend/dtos/state/order.py`
- Implement minimal DTO

#### Phase 3: Refactor
- Add docstrings
- Optimize validators

---

## 10. Lean Design Notes

**NOT included (per lean principles):**
- ❌ `causality` - Separate concern (StrategyJournal)
- ❌ `strategy_id` - Available via parent_group_id → TradePlan lookup
- ❌ `metadata` - No concrete consumer
- ❌ `average_fill_price` - Computed from Fills, not stored on Order
- ❌ `filled_quantity` - Computed from Fills, not stored on Order

**Why lean?**
- Order = intent state machine
- Fill = actual execution reality
- Aggregations computed on-demand, not stored redundantly

---

## 11. Verification Checklist

### Design Document
- [x] All sections completed
- [x] Reviewed against TRADE_LIFECYCLE.md
- [x] Reviewed against EXECUTION_FLOW.md
- [x] Lean design rationale documented

### Implementation (future)
- [ ] File created: `backend/dtos/state/order.py`
- [ ] ID generator added
- [ ] Enums added
- [ ] Tests written and passing
- [ ] Integration tested

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|--------|
| 1.0 | 2025-12-01 | AI Agent | Initial design document |
