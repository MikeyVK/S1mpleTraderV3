<!-- filepath: docs/development/backend/dtos/PLATFORM_DATA_DTO_DESIGN.md -->
# PlatformDataDTO Design Document

**Status:** ✅ Implemented (Clean)  
**Version:** 1.0  
**Last Updated:** 2025-12-01

---

## 1. Identity

| Aspect | Value |
|--------|-------|
| **DTO Name** | PlatformDataDTO |
| **ID Prefix** | N/A (uses Origin.id) |
| **Layer** | Platform |
| **File Path** | `backend/dtos/shared/platform_data.py` |
| **Status** | ✅ Implemented |

---

## 2. Contract

| Role | Component |
|------|-----------|
| **Producer** | DataProvider (Tick/News/Schedule providers) |
| **Consumer(s)** | FlowInitiator |
| **Trigger** | Platform data received (tick, news, schedule event) |

**Architectural Role (per EXECUTION_FLOW.md):**
- Minimal envelope for DataProvider → FlowInitiator communication
- Wraps provider DTOs with origin and timestamp
- FlowInitiator stores in StrategyCache and initiates strategy flow

---

## 3. Fields

| Field | Type | Req | Producer | Consumer | Validation |
|-------|------|-----|----------|----------|------------|
| `origin` | `Origin` | ✅ | DataProvider | FlowInitiator, CausalityChain | Type-safe origin (TICK/NEWS/SCHEDULE) |
| `timestamp` | `datetime` | ✅ | DataProvider | FlowInitiator | Point-in-time for cache initialization |
| `payload` | `BaseModel` | ✅ | DataProvider | Strategy Workers | Provider DTO (CandleWindow, etc.) |

---

## 4. Causality

| Aspect | Value |
|--------|-------|
| **Category** | Platform (birth of data) |
| **Has causality field** | ❌ NO - This IS the origin |
| **ID tracked in CausalityChain** | `origin.id` is copied to CausalityChain.origin |

**Origin Propagation:**
```python
# FlowInitiator copies origin to CausalityChain
causality = CausalityChain(origin=platform_data.origin)
```

---

## 5. Immutability

| Decision | Rationale |
|----------|-----------|
| **frozen** | `True` |
| **Why** | Pure data envelope - never modified after creation. |

---

## 6. Examples

### Tick Data
```json
{
  "origin": {
    "id": "TCK_20251201_143000_abc123",
    "type": "TICK"
  },
  "timestamp": "2025-12-01T14:30:00Z",
  "payload": {
    "symbol": "BTC_USDT",
    "timeframe": "1h",
    "open": 99500.00,
    "high": 100200.00,
    "low": 99200.00,
    "close": 100000.00,
    "volume": 1234.56
  }
}
```

### News Data
```json
{
  "origin": {
    "id": "NWS_20251201_150000_def456",
    "type": "NEWS"
  },
  "timestamp": "2025-12-01T15:00:00Z",
  "payload": {
    "headline": "Fed announces rate decision",
    "sentiment": "neutral",
    "source": "Reuters"
  }
}
```

---

## 7. Dependencies

- `backend/dtos/shared/origin.py` → `Origin`
- `pydantic.BaseModel`
- `datetime.datetime`

---

## 8. Breaking Changes

None required. DTO is clean and follows architectural guidelines.

---

## 9. Verification Checklist

- [x] Follows lean DTO principles
- [x] Uses typed Origin (not raw string)
- [x] frozen=True
- [x] No unnecessary fields

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|--------|
| 1.0 | 2025-12-01 | AI Agent | Initial design document |
