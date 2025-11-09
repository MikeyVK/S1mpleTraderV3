# StrategyLedger - Preliminary Design

**Status:** Preliminary - Architectural Contract  
**Versie:** 0.1  
**Datum:** 2025-11-08

---

## 1. Scope & Responsibility

**What StrategyLedger IS:**
- Pure persistence layer for order/trade lifecycle
- Disk-based storage (stateful)
- Injected dependency (NOT worker in event chain)
- Queried/updated by ExecutionHandler

**What StrategyLedger IS NOT:**
- ❌ NOT a worker in event chain
- ❌ NO knowledge of CausalityChain structure
- ❌ NO direct event handling

---

## 2. Core Operations

**Order Management:**
- `record_order(order_id, order_details)` - Store order placement
- `update_order_fill(order_id, fill_data)` - Update with fill
- `update_order_rejection(order_id, reason)` - Mark rejected
- `get_order(order_id)` - Query order state

**Trade Management:**
- `create_trade(trade_id, order_ids)` - Create from fills
- `update_trade(trade_id, updates)` - Modify existing
- `close_trade(trade_id, exit_data)` - Mark closed
- `get_trade(trade_id)` - Query trade state

**Position Management:**
- `get_open_positions()` - Current positions
- `get_position_exposure(symbol)` - Net exposure

---

## 3. Event Publishing

**Publishes:**
- `STRATEGY_LEDGER_UPDATED` - After every state change
  - Payload: `{ event_type: ORDER_PLACED | ORDER_FILLED | ORDER_REJECTED | TRADE_CREATED | ... }`

**Does NOT listen to events** (ExecutionHandler calls methods directly)

---

## 4. Storage Architecture

**Persistence:**
- Disk-based ledger (JSON/SQLite/Parquet - TBD)
- ACID guarantees for order/trade state
- Queryable for historical analysis

---

## 5. Integration Points

**Used by:**
- ExecutionHandler (primary user)
- Emergency scenarios (direct queries)

**Context Storage:**
- Stores own context in StrategyCache (under order_id/trade_id keys)
- NO CausalityChain storage (lives in ExecutionHandler)

---

## 6. Open Questions

1. Storage format: JSON vs SQLite vs Parquet?
2. Transaction boundaries: Per-order or per-batch?
3. Query API: Sync vs async?
4. Historical data retention policy?

---

## 7. Related Documents

- `CAUSALITY_CHAIN_DESIGN.md` - CausalityChain scope
- `STRATEGY_JOURNAL_WRITER_DESIGN.md` - Journal correlation
- `FLOW_TERMINATOR_DESIGN.md` - Event publishing
