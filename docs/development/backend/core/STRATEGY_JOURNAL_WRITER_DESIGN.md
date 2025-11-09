# StrategyJournalWriter - Preliminary Design

**Status:** Preliminary - Architectural Contract  
**Versie:** 0.1  
**Datum:** 2025-11-08

---

## 1. Scope & Responsibility

**What StrategyJournalWriter IS:**
- Platform worker (fixed per ExecutionEnvironment)
- Stateful logger (disk-based journal)
- Correlates causality (WHY) ↔ trade lifecycle (WHAT)
- Logs complete story for quant analysis

**What StrategyJournalWriter IS NOT:**
- ❌ NOT user-configurable (platform component)
- ❌ NO business logic (pure logger)
- ❌ NO state modification (read-only from ledger/cache)

---

## 2. Core Operations

**Journal Writing:**
- `write_order_placed(order_id, causality)` - Log order with intent
- `write_order_filled(order_id, fill_data)` - Log fill (correlates via order_id)
- `write_order_rejected(order_id, reason)` - Log exchange rejection
- `write_trade_opened(trade_id)` - Log trade birth
- `write_trade_modified(trade_id, changes)` - Log trade adjustment
- `write_trade_closed(trade_id, pnl)` - Log trade death
- `write_signal_rejected(causality, reason)` - Log strategy rejection

**Correlation Logic:**
- Query StrategyCache via CausalityChain IDs for complete story
- Query StrategyLedger for trade reality
- Combine: causality + reality → journal entry

---

## 3. Event Handling

**Listens to:**
- `STRATEGY_LEDGER_UPDATED` - Primary trigger
  - Extracts order_id/trade_id from payload
  - Queries StrategyCache for CausalityChain (via order_id)
  - Reconstructs complete causality story
  - Writes journal entry

**Does NOT publish events** (pure consumer)

---

## 4. Journal Architecture

**Storage:**
- Disk-based journal (append-only)
- Format: JSON Lines / Parquet (TBD)
- Immutable entries (audit trail)

**Entry Structure:**
```
{
  "entry_id": "JRN_...",
  "event_type": "ORDER_PLACED | ORDER_FILLED | ...",
  "timestamp": "...",
  
  "causality": {
    "tick_id": "...",
    "signal_ids": [...],
    "order_id": "..."
  },
  
  "reality": {
    "order_id": "...",
    "status": "...",
    "fills": [...]
  },
  
  "context": {
    "signal_details": {...},  // From StrategyCache
    "risk_details": {...},
    "plan_details": {...}
  }
}
```

---

## 5. Integration Points

**Data Sources:**
- StrategyLedger (via STRATEGY_LEDGER_UPDATED event)
- StrategyCache (via CausalityChain IDs)

**Consumers:**
- Quant analysis tools (read-only)
- Backtest analyzer
- Performance metrics

---

## 6. Open Questions

1. Journal format: JSON Lines vs Parquet?
2. Retention policy: Forever vs time-based?
3. Compression: Real-time vs batch?
4. Query API: Direct file access vs service?
5. How to handle missing cache entries (expired)?

---

## 7. Related Documents

- `CAUSALITY_CHAIN_DESIGN.md` - CausalityChain structure
- `STRATEGY_LEDGER_DESIGN.md` - Ledger integration
- `FLOW_TERMINATOR_DESIGN.md` - Event flow
