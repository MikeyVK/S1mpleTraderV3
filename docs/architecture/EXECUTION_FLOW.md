# Execution Flow Architecture - S1mpleTraderV3

**Status:** Architectural Contract - Definitive  
**Version:** 2.0  
**Last Updated:** 2025-11-27

---

## Executive Summary

This document describes the **complete execution flow** within a strategy - two parallel flows that both start via DataProvider → FlowInitiator. This document is **event bus agnostic** and focuses on technical data flow.

**Flow 1: Sync Strategy Flow (Market Data → Order Placement)**
```
ExchangeConnector (public websocket: market ticks)
    ↓ 
DataProvider → [_candle_btc_eth_ready]
    ↓ 
FlowInitiator → [CANDLE_STREAM_DATA_READY] → StrategyCache
    ↓
Context Workers → Signal Detector / Risk Monitor → StrategyPlanner
    ↓
TradePlanners (Entry/Size/Exit) → ExecutionPlanner
    ↓
ExecutionPlanner → ExecutionDirective → ExecutionWorker
    ↓
ExecutionWorker 
    ├→ Queries StrategyLedger for existing state (MODIFY/CLOSE)
    ├→ Registers containers (ExecutionGroup, Order)
    ├→ IExecutionConnector (REST API: places order)
    └→ Records order in StrategyLedger
    ↓
StrategyJournalWriter
    ├→ Retrieves CausalityChain from StrategyCache (via OrderID)
    └→ Writes journal entry: causality + order_id → causality persistence
    ↓
FlowTerminator
```

**Flow 2: Async Exchange Reply Flow (Fills/Rejections → Trade Reality)**
```
ExchangeConnector (private websocket: fills/rejections)
    ↓ 
DataProvider → [_reply_from_exchange]
    ↓ 
FlowInitiator → [EXCHANGE_REPLY] → StrategyCache
    ↓
ExecutionWorker
    ├→ Queries StrategyLedger for order context
    ├→ Generates FillID (if fill)
    └→ Updates StrategyLedger with fill/rejection
    ↓
StrategyJournalWriter
    ├→ Retrieves CausalityChain from previous journal entry (via OrderID lookup)
    └→ Writes journal entry: causality + order_id + fill_id → complete trade story
    ↓
FlowTerminator
```

**SRP Separation:**
- **StrategyLedger**: Persists order/fill/trade reality ONLY (NO causality storage) - owns all containers
- **StrategyJournalWriter**: Persists causality + correlates order_ids + fill_ids
- **FillID**: Symmetric ID (FIL_...) - captures actual execution (may differ from order)
- **Quant Analysis**: Cross-query StrategyJournal ↔ StrategyLedger via order_id/fill_id

**Key Principle:** 
> Order reality (StrategyLedger) and causality (StrategyJournal) are separate persistence concerns, correlated via order_id + fill_id for complete trade story analysis.

**Cross-reference:** [TRADE_LIFECYCLE.md](TRADE_LIFECYCLE.md) (container ownership), [WORKER_TAXONOMY.md](WORKER_TAXONOMY.md) (ExecutionWorker responsibilities)

---

## 1. Sync Flow - Market Data to Order Placement

### 1.1 Complete Flow Diagram

```mermaid
sequenceDiagram
    participant EC as ExchangeConnector<br/>(public websocket)
    participant DP as DataProvider
    participant FI as FlowInitiator
    participant SC as StrategyCache
    participant SW as Strategy Workers<br/>(Context/Signal/Risk)
    participant SP as StrategyPlanner
    participant TP as TradePlanners<br/>(Entry/Size/Exit)
    participant EP as ExecutionPlanner<br/>(4th TradePlanner)
    participant EW as ExecutionWorker
    participant SL as StrategyLedger<br/>(disk)
    participant XC as IExecutionConnector<br/>(REST API)
    participant SJ as StrategyJournalWriter<br/>(disk)
    participant FT as FlowTerminator

    EC->>DP: market tick (websocket)
    DP->>FI: [_candle_btc_eth_ready]
    FI->>FI: Create Origin DTO
    FI->>SC: Store PlatformDataDTO
    FI->>SW: [CANDLE_STREAM_DATA_READY]
    
    SW->>SP: Signals + Risks
    SP->>SP: Create CausalityChain<br/>(origin + signal_ids + risk_ids)
    SP->>TP: StrategyDirective + Causality
    SP->>SJ: Opportunity/signal rejected
    
    TP->>EP: EntryPlan + SizePlan + ExitPlan
    EP->>EP: Aggregate plans + select algorithm
    EP->>EW: ExecutionDirective + Causality
    
    Note over EW,SL: ExecutionWorker queries existing state if needed
    EW->>SL: Query existing ExecutionGroup/Orders (MODIFY/CLOSE)
    SL-->>EW: Current state
    
    EW->>EW: Generate OrderID
    EW->>EW: Add OrderID to CausalityChain
    EW->>SL: Register ExecutionGroup (on-demand)
    EW->>SL: Register Order container
    EW->>XC: Place order (REST)
    EW->>SL: Record order with exchange_order_id
    EW->>SC: Store order context + causality
    
    EW->>SJ: Order recorded
    SJ->>SC: Get causality via OrderID

    alt Order
        SJ->>SJ: Write journal entry<br/>causality + order_id
    else Rejection
        SJ->>SJ: Write journal entry<br/>causality + rejection
    end

    SJ->>FT: Complete
    FT->>FT: Terminate sync flow
```

### 1.2 Key Operations

**FlowInitiator:**
- Creates Origin DTO from platform data
- Stores PlatformDataDTO in StrategyCache
- Initiates strategy flow with CANDLE_STREAM_DATA_READY event

**StrategyPlanner:**
- Creates CausalityChain with Origin (from PlatformDataDTO)
- Adds signal_ids, risk_ids during flow
- Propagates causality through pipeline

**ExecutionPlanner (4th TradePlanner):**
- Aggregates EntryPlan + SizePlan + ExitPlan
- Selects execution algorithm
- Produces ExecutionDirective for ExecutionWorker
- Has descriptive read access to StrategyLedger

**ExecutionWorker:**
- Generates OrderID: `ORD_{YYYYMMDD}_{HHMMSS}_{hash}`
- Adds OrderID to CausalityChain: `causality.order_ids.append(order_id)`
- Queries StrategyLedger for existing state (MODIFY/CLOSE scenarios)
- Registers containers (ExecutionGroup, Order) on-demand
- Places order via IExecutionConnector
- Records order in StrategyLedger (NO causality storage!)
- Stores order context + causality in StrategyCache

**StrategyLedger:**
- Persists order reality: status, details, timestamps
- Owns all containers (Trade, ExecutionGroup, Order, Fill)
- NO causality storage (SRP separation)
- Queryable by ExecutionWorker (both sync and async flows)

**StrategyJournalWriter:**
- Retrieves CausalityChain from StrategyCache (via OrderID)
- Retrieves Context DTO's produced by StrategyWorkers from StrategyCache
- Writes journal entry: causality + order_id correlation + Context
- Enables later quant analysis

---

## 2. Async Flow - Exchange Reply to Trade Reality

### 2.1 Complete Flow Diagram

```mermaid
sequenceDiagram
    participant EC as ExchangeConnector<br/>(private websocket)
    participant DP as DataProvider
    participant FI as FlowInitiator
    participant SC as StrategyCache
    participant EW as ExecutionWorker
    participant SL as StrategyLedger<br/>(disk)
    participant SJ as StrategyJournalWriter<br/>(disk)
    participant FT as FlowTerminator

    EC->>DP: fill/rejection (websocket)
    DP->>FI: [_reply_from_exchange]
    FI->>SC: Store PlatformDataDTO
    FI->>EW: [EXCHANGE_REPLY]
    
    EW->>SL: Query order context (via order_id)
    SL-->>EW: Order context
    
    alt Fill received
        EW->>EW: Generate FillID
        EW->>SL: Register Fill container
        EW->>SL: Update order status
    else Rejection received
        EW->>SL: Update order with rejection_reason
    end
    
    EW->>SC: Update order context
    
    EW->>SJ: Order updated
    SJ->>SJ: Query previous journal entry<br/>(via OrderID)
    SJ->>SJ: Retrieve CausalityChain
    
    alt Fill
        SJ->>SJ: Write journal entry<br/>causality + order_id + fill_id<br/>→ complete trade story
    else Rejection
        SJ->>SJ: Write journal entry<br/>causality + order_id + rejection<br/>→ failed attempt story
    end
    
    SJ->>FT: Complete
    FT->>FT: Terminate async flow
```

### 2.2 Key Operations

**FlowInitiator:**
- Stores PlatformDataDTO in StrategyCache
- Triggers EXCHANGE_REPLY event

**ExecutionWorker (Async):**
- Queries StrategyLedger for order context
- Generates FillID: `FIL_{YYYYMMDD}_{HHMMSS}_{hash}` (if fill)
- Registers Fill container in StrategyLedger
- Updates order status with fill/rejection details

**FillID Rationale:**
- Symmetric ID captures actual execution
- May differ from order (partial fills, price deviation)
- Enables precise trade reconstruction

**StrategyJournalWriter (Async):**
- Queries previous journal entry via OrderID
- Retrieves CausalityChain from previous entry
- Retrieves Context DTO's produced by StrategyWorkers from StrategyCache
- Writes updated entry: causality + order_id + fill_id + context
- Creates complete trade story: intent → order → fill → outcome

---

## 3. SRP Component Responsibilities

### 3.1 Responsibility Matrix

| Component | Responsibility | Stores Causality? | Stores Reality? |
|-----------|---------------|-------------------|-----------------|
| **ExecutionPlanner** | Aggregates plans, selects algorithm | Via StrategyDirective | No |
| **ExecutionWorker** | Creates OrderID/FillID, executes orders | Via StrategyCache | No |
| **StrategyLedger** | Persists order/fill/trade reality | ❌ NO | ✅ YES |
| **StrategyJournalWriter** | Persists causality + correlates IDs | ✅ YES | ❌ NO |
| **StrategyCache** | Temporary context storage | ✅ YES (temp) | ✅ YES (temp) |

### 3.2 Storage Architecture

```mermaid
graph TB
    subgraph "Sync Flow"
        EW1[ExecutionWorker] --> SC[StrategyCache<br/>Temporary]
        EW1 --> SL[StrategyLedger<br/>Disk - Reality]
        SC --> SJ1[StrategyJournalWriter]
        SJ1 --> SJDB[StrategyJournal<br/>Disk - Causality]
    end
    
    subgraph "Async Flow"
        EW2[ExecutionWorker] --> SL
        SL --> SJ2[StrategyJournalWriter]
        SJ2 --> SJDB
        SJDB --> SJ2
    end
    
    subgraph "Quant Analysis"
        SJDB -.cross-query.-> SL
        Q[TradeExplorer UI] --> SJDB
        Q --> SL
    end
    
    style SL fill:#f9f,stroke:#333
    style SJDB fill:#9ff,stroke:#333
    style SC fill:#ff9,stroke:#333
```

### 3.3 ID Propagation Pattern

```
Origin (in PlatformDataDTO)
    ↓
CausalityChain.origin = Origin
    ↓
Signal/Risk/Plan IDs added
    ↓
ExecutionPlanner aggregates plans, produces ExecutionDirective
    ↓
ExecutionWorker creates OrderID
    ↓
CausalityChain.order_ids.append(order_id)
    ↓
StrategyCache stores: order_id → {causality, order_details}
    ↓
StrategyJournalWriter writes: causality + order_id
    ↓
(async) ExecutionWorker creates FillID
    ↓
StrategyJournalWriter writes: causality + order_id + fill_id
    ↓
Complete trade story: WHY → WHAT → HOW → OUTCOME
```

---

## 4. Quant Analysis Integration

### 4.1 Cross-Query Pattern

```python
# Quant retrieves complete trade story
journal_entry = strategy_journal.get_entry(order_id="ORD_...")
causality = journal_entry.causality
order_details = journal_entry.order_id
fill_ids = journal_entry.fill_ids

# Query ledger for reality
order_reality = strategy_ledger.get_order(order_id)
fills_reality = [strategy_ledger.get_fill(fid) for fid in fill_ids]

# Complete analysis
story = {
    "causality": {
        "origin": causality.origin,  # WHY (tick/news/schedule)
        "signals": [cache.get(sid) for sid in causality.signal_ids],  # WHAT detected
        "risks": [cache.get(rid) for rid in causality.risk_ids],  # WHAT assessed
        "strategy": cache.get(causality.strategy_directive_id),  # WHAT decided
    },
    "reality": {
        "order_intent": order_reality,  # WHAT ordered
        "fills": fills_reality,  # WHAT executed
        "deviation": calculate_slippage(order_reality, fills_reality)  # HOW different
    }
}
```

### 4.2 Analysis Questions Enabled

**Causality Analysis:**
- Which origin types (tick/news/schedule) have best win rate?
- Which signal combinations lead to profitable trades?
- Which risk assessments prevent bad trades?

**Execution Analysis:**
- How much slippage between order intent and fill reality?
- Which execution algorithms minimize slippage?
- Which market conditions cause highest deviation?

**Complete Story:**
- Why did this trade succeed/fail? (causality → reality correlation)
- Which decision points were optimal/suboptimal?
- How can strategy improve based on past patterns?

---

## 5. Related Documents

- **[TRADE_LIFECYCLE.md](TRADE_LIFECYCLE.md)** - Container hierarchy and Ledger access patterns
- **[WORKER_TAXONOMY.md](WORKER_TAXONOMY.md)** - Worker categories and responsibilities
- **[PIPELINE_FLOW.md](PIPELINE_FLOW.md)** - Complete strategy pipeline (phases 0-4)
- **[CAUSALITY_CHAIN_DESIGN.md](../development/CAUSALITY_CHAIN_DESIGN.md)** - CausalityChain structure and propagation

---

## 6. Key Architectural Decisions

1. **Dual Flow Architecture**: Sync (strategy) + Async (exchange reply) both terminate via FlowTerminator
2. **SRP Separation**: StrategyLedger (reality) ≠ StrategyJournal (causality), correlated via IDs
3. **ID Symmetry**: OrderID + FillID enable precise execution tracking
4. **FlowInitiator Dual Role**: Creates StrategyCache for both sync and async flows
5. **StrategyJournalWriter Before FlowTerminator**: Recording happens before termination (SRP)
6. **No Batch IDs in Causality**: Batching is pipeline plumbing, not causality
7. **Origin DTO**: Type-safe origin reference replaces tick_id/news_id/schedule_id
8. **ExecutionPlanner as 4th TradePlanner**: Aggregates Entry/Size/Exit plans + selects execution algorithm
9. **ExecutionWorker Container Ownership**: Full CRUD access to StrategyLedger, registers containers on-demand
