<!-- filepath: docs/development/backend/dtos/SIGNAL_DESIGN.md -->
# Signal Design Document

**Status:** ✅ Compliant  
**Version:** 1.1  
**Last Updated:** 2025-12-07

---

## 1. Identity

| Aspect | Value |
|--------|-------|
| **DTO Name** | Signal |
| **ID Prefix** | `SIG_` |
| **Layer** | Analysis (Pre-Causality) |
| **File Path** | `backend/dtos/strategy/signal.py` |
| **Status** | ✅ Compliant |

---

## 2. Contract

| Role | Component |
|------|-----------|
| **Producer** | SignalDetector (plugin workers) |
| **Consumer(s)** | StrategyPlanner (via EventBus) |
| **Trigger** | Technical pattern detected in market data |

**Architectural Role (per WORKER_TAXONOMY.md):**
- SignalDetector reads TickCache → Applies **subjective interpretation** → Publishes Signal to EventBus
- Signal is a **detection fact** at a specific point in time
- NO trade_id yet - that's created by StrategyPlanner if approved

---

## 3. Fields

| Field | Type | Req | Producer | Consumer | Validation |
|-------|------|-----|----------|----------|------------|
| `signal_id` | `str` | ✅ | Auto-generated | StrategyPlanner, Journal | Pattern: `^SIG_\d{8}_\d{6}_[0-9a-f]{8}$` |
| `timestamp` | `datetime` | ✅ | SignalDetector | StrategyPlanner | UTC, timezone-aware |
| `symbol` | `str` | ✅ | SignalDetector | StrategyPlanner | Pattern: `^[A-Z]+_[A-Z]+$` (e.g., `BTC_USDT`) |
| `direction` | `Literal["long", "short"]` | ✅ | SignalDetector | StrategyPlanner | Analysis direction (not execution) |
| `signal_type` | `str` | ✅ | SignalDetector | StrategyPlanner | UPPER_SNAKE_CASE, 3-25 chars |
| `confidence` | `Decimal` | ❌ | SignalDetector | StrategyPlanner | Range [0.0, 1.0] |

---

## 4. Causality

| Aspect | Value |
|--------|-------|
| **Category** | **Pre-causality** (detection fact) |
| **Has causality field** | ❌ **NO** - Signal is BEFORE causality chain starts |
| **ID tracked in CausalityChain** | `signal_id` added by StrategyPlanner when decision made |

**Critical Design Decision:**
Per EXECUTION_FLOW.md and PIPELINE_FLOW.md, Signal is a **pre-causality DTO**:
- Signal represents a **detection fact** ("pattern X detected at time T")
- CausalityChain is created by **StrategyPlanner** (first post-causality component)
- StrategyPlanner collects `signal_ids` from consumed signals into the causality chain

**Status:** ✅ Correctly implemented - Signal has NO causality field.

---

## 5. Immutability

| Decision | Rationale |
|----------|-----------|
| **frozen** | `True` |
| **Why** | Pure detection fact - never modified after creation. Audit trail integrity. |

---

## 6. Examples

```json
{
  "signal_id": "SIG_20251201_143022_a1b2c3d4",
  "timestamp": "2025-12-01T14:30:22Z",
  "symbol": "BTC_USDT",
  "direction": "long",
  "signal_type": "FVG_ENTRY",
  "confidence": "0.85"
}
```

**Note:** No `causality` field - Signal is pre-causality.

---

## 7. Dependencies

- `backend/utils/id_generators.py` → `generate_signal_id()`
- `pydantic.BaseModel`
- `decimal.Decimal`
- `datetime.datetime`

---

## 8. Breaking Changes Required

**Status:** ✅ ALL COMPLETED (verified 2025-12-07)

| Original Issue | Resolution | Status |
|----------------|------------|--------|
| `causality: CausalityChain` | Removed - Signal is pre-causality | ✅ Done |
| `asset: str` | Renamed to `symbol: str` | ✅ Done |
| Pattern `BTC/EUR` | Changed to `BTC_USDT` format | ✅ Done |
| `confidence: float` | Changed to `Decimal` | ✅ Done |

### Migration Checklist

- [x] Remove `causality` field from Signal class
- [x] Rename `asset` → `symbol`
- [x] Update symbol validation pattern (underscore separator)
- [x] Change `confidence` from `float` to `Decimal`
- [x] Update docstrings to reflect pre-causality role
- [x] Remove `CausalityChain` import
- [x] Update all tests in `tests/unit/dtos/strategy/test_signal.py`
- [x] Update examples in json_schema_extra

---

## 9. TDD Implementation Steps

### Phase 1: Update Tests (RED)

```python
# tests/unit/dtos/strategy/test_signal.py

class TestSignalCreation:
    def test_create_without_causality(self) -> None:
        """Should create Signal without causality field."""
        signal = Signal(
            timestamp=datetime.now(timezone.utc),
            symbol="BTC_USDT",  # NEW: was 'asset'
            direction="long",
            signal_type="FVG_ENTRY"
        )
        assert not hasattr(signal, 'causality')  # No causality!
        
    def test_symbol_uses_no_separator(self) -> None:
        """Symbol should use format BTC_USDT (underscore separator)."""
        signal = Signal(
            timestamp=datetime.now(timezone.utc),
            symbol="BTC_USDT",  # Underscore separator
            direction="long",
            signal_type="BREAKOUT"
        )
        assert signal.symbol == "BTC_USDT"

class TestSignalFieldValidation:
    def test_confidence_is_decimal(self) -> None:
        """Confidence should be Decimal for precision."""
        signal = Signal(
            timestamp=datetime.now(timezone.utc),
            symbol="ETH_USDT",
            direction="short",
            signal_type="REVERSAL",
            confidence=Decimal("0.75")
        )
        assert isinstance(signal.confidence, Decimal)
```

### Phase 2: Implement Changes (GREEN)

1. Remove `causality` field
2. Rename `asset` → `symbol`
3. Update validation pattern
4. Change `confidence` type to `Decimal`

### Phase 3: Refactor

- Update docstrings
- Update examples
- Clean up imports

---

## 10. Verification Checklist

### Design Document
- [x] All 8 sections completed
- [x] Reviewed against WORKER_TAXONOMY.md
- [x] Reviewed against PIPELINE_FLOW.md
- [x] Breaking changes documented

### Implementation
- [x] File updated: `backend/dtos/strategy/signal.py`
- [x] Follows CODE_STYLE.md structure
- [x] All fields match design document
- [x] Validators updated
- [x] model_config correct (frozen=True)

### Tests
- [x] Test file updated
- [x] Creation tests pass
- [x] ID validation tests pass
- [x] Field validation tests pass
- [x] Immutability tests pass
- [x] Serialization tests pass
- [x] **32 tests passing** (verified 2025-12-07)

### Integration
- [x] No import errors in dependent modules

### Quality Gates
- [x] `pytest tests/unit/dtos/strategy/test_signal.py` - 32 PASS
- [x] `pyright backend/dtos/strategy/signal.py` - 0 errors

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|--------|
| 1.1 | 2025-12-07 | AI Agent | Verified compliant - all breaking changes already implemented |
| 1.0 | 2025-12-01 | AI Agent | Initial design document |
