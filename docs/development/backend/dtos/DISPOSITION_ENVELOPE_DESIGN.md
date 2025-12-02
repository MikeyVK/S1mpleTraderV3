<!-- filepath: docs/development/backend/dtos/DISPOSITION_ENVELOPE_DESIGN.md -->
# DispositionEnvelope Design Document

**Status:** ✅ Implemented  
**Version:** 1.0  
**Last Updated:** 2025-12-01

---

## 1. Identity

| Aspect | Value |
|--------|-------|
| **DTO Name** | DispositionEnvelope |
| **ID Prefix** | N/A (flow control, not tracked) |
| **Layer** | Shared (Cross-Cutting) |
| **File Path** | `backend/dtos/shared/disposition_envelope.py` |
| **Status** | ✅ Implemented |

---

## 2. Contract

| Role | Component |
|------|-----------|
| **Producer** | All Workers (return value) |
| **Consumer(s)** | EventAdapter (interprets disposition) |
| **Trigger** | Worker completes processing |

**Architectural Role (per WORKER_TAXONOMY.md):**
- Standardized return type for all workers
- Enables event-driven flow control
- Decouples workers from EventBus
- Part of "Platgeslagen Orkestratie" architecture

---

## 3. Fields

| Field | Type | Req | Producer | Consumer | Validation |
|-------|------|-----|----------|----------|------------|
| `disposition` | `Literal["CONTINUE", "PUBLISH", "STOP"]` | ✅ | Worker | EventAdapter | Default: "CONTINUE" |
| `event_name` | `str \| None` | ❌ | Worker | EventAdapter | Required if PUBLISH, UPPER_SNAKE_CASE |
| `event_payload` | `BaseModel \| None` | ❌ | Worker | EventAdapter | Optional System DTO |

---

## 4. Dispositions

| Disposition | Meaning | EventAdapter Action |
|-------------|---------|---------------------|
| `CONTINUE` | Continue flow, data in TickCache | Route to next worker in chain |
| `PUBLISH` | Publish event on EventBus | Publish event_name with optional payload |
| `STOP` | Terminate this flow branch | End processing, no further routing |

---

## 5. Causality

| Aspect | Value |
|--------|-------|
| **Category** | Flow control (not tracked) |
| **Has causality field** | ❌ NO - Pure flow control mechanism |
| **ID tracked in CausalityChain** | N/A |

---

## 6. Immutability

| Decision | Rationale |
|----------|-----------|
| **frozen** | Not explicitly set (default Pydantic behavior) |
| **Why** | Flow control envelope - typically short-lived |

---

## 7. Examples

### ContextWorker - Continue Flow
```python
DispositionEnvelope(disposition="CONTINUE")
```

### SignalDetector - Publish Signal
```python
from backend.dtos.strategy.signal import Signal

signal = Signal(
    timestamp=datetime.now(timezone.utc),
    symbol="BTC_USDT",
    direction="long",
    signal_type="BREAKOUT"
)
DispositionEnvelope(
    disposition="PUBLISH",
    event_name="SIGNAL_GENERATED",
    event_payload=signal
)
```

### RiskMonitor - Emergency Halt
```python
DispositionEnvelope(
    disposition="PUBLISH",
    event_name="EMERGENCY_HALT"
    # No payload needed for pure signal
)
```

### Stop Flow
```python
DispositionEnvelope(disposition="STOP")
```

---

## 8. Event Name Convention

- Pattern: UPPER_SNAKE_CASE
- Length: 3-100 characters
- Reserved prefixes (blocked): `SYSTEM_`, `INTERNAL_`, `_`

---

## 9. Dependencies

- `pydantic.BaseModel`
- No other DTOs (standalone)

---

## 10. Breaking Changes

None required. DTO is clean and follows architectural guidelines.

---

## 11. Verification Checklist

- [x] Follows lean DTO principles
- [x] Clear disposition semantics
- [x] Event name validation
- [x] Decouples workers from EventBus

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|--------|
| 1.0 | 2025-12-01 | AI Agent | Initial design document |
