# FlowTerminator - Preliminary Design

**Status:** Preliminary - Architectural Contract  
**Versie:** 0.1  
**Datum:** 2025-11-08

---

## 1. Scope & Responsibility

**What FlowTerminator IS:**
- Platform worker (end of strategy flow)
- Lightweight event publisher
- Flow completion marker
- NO I/O operations (pure coordinator)

**What FlowTerminator IS NOT:**
- ❌ NOT a recorder (StrategyJournalWriter does that)
- ❌ NO disk operations
- ❌ NO business logic

---

## 2. Core Operations

**Flow Termination:**
- `on_flow_complete(batch: ExecutionDirectiveBatch)` - Strategy flow ended
- `on_flow_rejected(causality: CausalityChain, reason: str)` - Strategy rejected signal

**Event Publishing:**
- Publishes `CAUSALITY_RECORDED` event
  - Lightweight marker: "Flow ended, causality captured"
  - Payload: Minimal (batch_id or causality summary)

---

## 3. Event Handling

**Listens to:**
- Last event in strategy flow (after ExecutionHandler completes)
  - Could be: EXECUTION_COMPLETE
  - Or: SIGNAL_REJECTED (early termination)

**Publishes:**
- `CAUSALITY_RECORDED` - Flow completion marker

---

## 4. SRP Rationale

**Why FlowTerminator does NOT record:**
- Recording = I/O operation (slow, blocking)
- FlowTerminator = pure coordinator (fast, non-blocking)
- StrategyJournalWriter = platform worker (separate concern)

**Flow Architecture:**
```
ExecutionHandler
    ↓
    ├→ StrategyLedger (persistence)
    └→ FlowTerminator (publishes event)
            ↓
        CAUSALITY_RECORDED
            ↓
        (StrategyJournalWriter listens separately via STRATEGY_LEDGER_UPDATED)
```

---

## 5. Integration Points

**Position in Pipeline:**
- Last worker in strategy flow
- After ExecutionHandler completes
- Before strategy flow terminates

**Event Consumers:**
- Platform monitoring (flow tracking)
- Metrics collection (flow duration)
- StrategyJournalWriter (indirect, via ledger updates)

---

## 6. Open Questions

1. Should FlowTerminator track flow metrics (duration, step count)?
2. Event payload: Full batch or just batch_id?
3. Error handling: What if ExecutionHandler fails?
4. Multiple termination points (rejected vs completed)?

---

## 7. Related Documents

- `CAUSALITY_CHAIN_DESIGN.md` - Section 4.4 (SRP separation)
- `STRATEGY_LEDGER_DESIGN.md` - Ledger updates
- `STRATEGY_JOURNAL_WRITER_DESIGN.md` - Recording happens here
