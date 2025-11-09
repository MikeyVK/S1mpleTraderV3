# ExecutionHandler - Preliminary Design

**Status:** Preliminary - Architectural Contract  
**Versie:** 0.1  
**Datum:** 2025-11-08

---

## 1. Scope & Responsibility

**What ExecutionHandler IS:**
- Platform worker in strategy flow
- Orchestrates order placement via ExchangeConnector
- Creates OrderID and adds to CausalityChain
- Uses StrategyLedger (injected) for persistence
- Handles async EXCHANGE_REPLY events
- Fills StrategyCache with execution context

**What ExecutionHandler IS NOT:**
- ❌ NOT stateful (StrategyLedger handles persistence)
- ❌ NO direct exchange communication (ExchangeConnector does that)
- ❌ NO business logic (executes directives as-is)

---

## 2. Core Operations

**Order Placement Flow:**
- `execute(directive: ExecutionDirective)` - Primary entry point
  - Generate OrderID
  - Add OrderID to CausalityChain
  - Use ExchangeConnector to place order
  - Record in StrategyLedger
  - Store context in StrategyCache

**Exchange Reply Handling:**
- `on_exchange_reply(reply: ExchangeReplyDTO)` - Async updates
  - Query StrategyLedger for order context
  - Update order state (fill/rejection)
  - Update CausalityChain with order status
  - Store updated context in StrategyCache

---

## 3. Event Handling

**Listens to:**
- Receives ExecutionDirective from pipeline
- `EXCHANGE_REPLY` - Async exchange responses (fills, rejections)

**Publishes:**
- No direct events (delegates to StrategyLedger)
- StrategyLedger publishes STRATEGY_LEDGER_UPDATED

---

## 4. Integration Points

**Dependencies (Injected):**
- `StrategyLedger` - Persistence layer
- `ExchangeConnector` - Exchange communication
- `StrategyCache` - Context storage

**Data Flow:**
```
ExecutionDirective (with CausalityChain)
    ↓
ExecutionHandler
    ├→ Generate OrderID
    ├→ Add OrderID to CausalityChain
    ├→ ExchangeConnector.place_order()
    ├→ StrategyLedger.record_order()
    └→ StrategyCache.store(order_id, context)
```

**Async Flow:**
```
EXCHANGE_REPLY event
    ↓
ExecutionHandler
    ├→ StrategyLedger.get_order(order_id)
    ├→ StrategyLedger.update_order_fill/rejection()
    └→ StrategyCache.update(order_id, updated_context)
```

---

## 5. OrderID Generation

**Format:**
- `ORD_{YYYYMMDD}_{HHMMSS}_{hash}` (from id_generators.py)
- Unique per order placement
- Added to CausalityChain for traceability

---

## 6. Context Storage

**StrategyCache Entries:**
- Key: `order_id`
- Value: Order context
  ```
  {
    "order_id": "ORD_...",
    "causality": CausalityChain,
    "order_details": {...},
    "status": "PENDING | FILLED | REJECTED",
    "fills": [...]
  }
  ```

---

## 7. Open Questions

1. OrderID generation: Handler responsibility or StrategyLedger?
2. Multiple orders per directive: How to handle?
3. Partial fills: Update CausalityChain per fill or only when complete?
4. Failed order placement: Retry logic or immediate failure?
5. Exchange timeout: How long to wait for reply?

---

## 8. Related Documents

- `STRATEGY_LEDGER_DESIGN.md` - Persistence integration
- `CAUSALITY_CHAIN_DESIGN.md` - CausalityChain structure
- `STRATEGY_JOURNAL_WRITER_DESIGN.md` - Journal correlation
- `FLOW_TERMINATOR_DESIGN.md` - Flow completion
