<!-- filepath: docs/development/backend/dtos/RISK_DESIGN.md -->
# Risk Design Document

**Status:** ✅ Compliant  
**Version:** 1.1  
**Last Updated:** 2025-12-07

---

## 1. Identity

| Aspect | Value |
|--------|-------|
| **DTO Name** | Risk |
| **ID Prefix** | `RSK_` |
| **Layer** | Analysis (Pre-Causality) |
| **File Path** | `backend/dtos/strategy/risk.py` |
| **Status** | ✅ Compliant |

---

## 2. Contract

| Role | Component |
|------|-----------|
| **Producer** | RiskMonitor (plugin workers) |
| **Consumer(s)** | StrategyPlanner (via EventBus) |
| **Trigger** | Risk condition detected (drawdown, stop loss, systemic risk) |

**Architectural Role (per WORKER_TAXONOMY.md):**
- RiskMonitor reads TickCache → Applies **subjective interpretation** → Publishes Risk to EventBus
- Risk is a **detection fact** representing a threat condition
- `affected_symbol = None` indicates system-wide risk (not asset-specific)

---

## 3. Fields

| Field | Type | Req | Producer | Consumer | Validation |
|-------|------|-----|----------|----------|------------|
| `risk_id` | `str` | ✅ | Auto-generated | StrategyPlanner, Journal | Pattern: `^RSK_\d{8}_\d{6}_[0-9a-f]{8}$` |
| `timestamp` | `datetime` | ✅ | RiskMonitor | StrategyPlanner | UTC, timezone-aware |
| `risk_type` | `str` | ✅ | RiskMonitor | StrategyPlanner | UPPER_SNAKE_CASE, 3-25 chars |
| `severity` | `Decimal` | ✅ | RiskMonitor | StrategyPlanner | Range [0.0, 1.0] |
| `affected_symbol` | `str \| None` | ❌ | RiskMonitor | StrategyPlanner | Pattern: `^[A-Z]+_[A-Z]+$` or `None` (system-wide) |

---

## 4. Causality

| Aspect | Value |
|--------|-------|
| **Category** | **Pre-causality** (detection fact) |
| **Has causality field** | ❌ **NO** - Risk is BEFORE causality chain starts |
| **ID tracked in CausalityChain** | `risk_id` added by StrategyPlanner to `risk_ids[]` |

**Critical Design Decision:**
Per EXECUTION_FLOW.md and PIPELINE_FLOW.md, Risk is a **pre-causality DTO**:
- Risk represents a **detection fact** ("drawdown breach detected at severity 0.9")
- CausalityChain is created by **StrategyPlanner** (first post-causality component)
- StrategyPlanner collects `risk_ids` from consumed risks into the causality chain

**Status:** ✅ Correctly implemented - Risk has NO causality field.

---

## 5. Immutability

| Decision | Rationale |
|----------|-----------|
| **frozen** | `True` |
| **Why** | Pure detection fact - never modified after creation. Audit trail integrity. |

---

## 6. Examples

### Asset-Specific Risk
```json
{
  "risk_id": "RSK_20251201_143500_b2c3d4e5",
  "timestamp": "2025-12-01T14:35:00Z",
  "risk_type": "STOP_LOSS_HIT",
  "severity": "0.90",
  "affected_symbol": "BTC_USDT"
}
```

### System-Wide Risk
```json
{
  "risk_id": "RSK_20251201_143510_c3d4e5f6",
  "timestamp": "2025-12-01T14:35:10Z",
  "risk_type": "EXCHANGE_CONNECTIVITY_LOST",
  "severity": "1.00",
  "affected_symbol": null
}
```

**Note:** No `causality` field - Risk is pre-causality.

---

## 7. Dependencies

- `backend/utils/id_generators.py` → `generate_risk_id()`
- `pydantic.BaseModel`
- `decimal.Decimal`
- `datetime.datetime`

---

## 8. Breaking Changes Required

**Status:** ✅ ALL COMPLETED (verified 2025-12-07)

| Original Issue | Resolution | Status |
|----------------|------------|--------|
| `causality: CausalityChain` | Removed - Risk is pre-causality | ✅ Done |
| `affected_asset: str` | Renamed to `affected_symbol: str` | ✅ Done |
| Pattern `BTC/EUR` | Changed to `BTC_USDT` format | ✅ Done |
| `severity: float` | Changed to `Decimal` | ✅ Done |

### Migration Checklist

- [x] Remove `causality` field from Risk class
- [x] Rename `affected_asset` → `affected_symbol`
- [x] Update symbol validation pattern (underscore separator)
- [x] Change `severity` from `float` to `Decimal`
- [x] Update docstrings to reflect pre-causality role
- [x] Remove `CausalityChain` import
- [x] Update all tests in `tests/unit/dtos/strategy/test_risk.py`
- [x] Update examples in json_schema_extra

---

## 9. TDD Implementation Steps

### Phase 1: Update Tests (RED)

```python
# tests/unit/dtos/strategy/test_risk.py

class TestRiskCreation:
    def test_create_without_causality(self) -> None:
        """Should create Risk without causality field."""
        risk = Risk(
            timestamp=datetime.now(timezone.utc),
            risk_type="DRAWDOWN_BREACH",
            severity=Decimal("0.75"),
            affected_symbol="BTC_USDT"  # NEW: was 'affected_asset'
        )
        assert not hasattr(risk, 'causality')  # No causality!
        
    def test_system_wide_risk_has_no_symbol(self) -> None:
        """System-wide risk should have affected_symbol=None."""
        risk = Risk(
            timestamp=datetime.now(timezone.utc),
            risk_type="EXCHANGE_DOWN",
            severity=Decimal("1.0"),
            affected_symbol=None
        )
        assert risk.affected_symbol is None

class TestRiskFieldValidation:
    def test_severity_is_decimal(self) -> None:
        """Severity should be Decimal for precision."""
        risk = Risk(
            timestamp=datetime.now(timezone.utc),
            risk_type="POSITION_RISK",
            severity=Decimal("0.65")
        )
        assert isinstance(risk.severity, Decimal)
        
    def test_symbol_uses_no_separator(self) -> None:
        """Symbol should use format BTC_USDT (underscore separator)."""
        risk = Risk(
            timestamp=datetime.now(timezone.utc),
            risk_type="STOP_LOSS_HIT",
            severity=Decimal("0.9"),
            affected_symbol="ETH_USDT"  # Underscore separator
        )
        assert risk.affected_symbol == "ETH_USDT"
```

### Phase 2: Implement Changes (GREEN)

1. Remove `causality` field
2. Rename `affected_asset` → `affected_symbol`
3. Update validation pattern
4. Change `severity` type to `Decimal`

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
- [x] File updated: `backend/dtos/strategy/risk.py`
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
- [x] **29 tests passing** (verified 2025-12-07)

### Integration
- [x] No import errors in dependent modules

### Quality Gates
- [x] `pytest tests/unit/dtos/strategy/test_risk.py` - 29 PASS
- [x] `pyright backend/dtos/strategy/risk.py` - 0 errors

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|--------|
| 1.1 | 2025-12-07 | AI Agent | Verified compliant - all breaking changes already implemented |
| 1.0 | 2025-12-01 | AI Agent | Initial design document |
