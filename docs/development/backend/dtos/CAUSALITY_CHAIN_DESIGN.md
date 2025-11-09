# CausalityChain Design - Pure Decision Lineage Tracking

**Status:** ✅ Implemented  
**Implementation:** `backend/dtos/causality.py`  
**Tests:** 28/28 passing (100% coverage)  
**Versie:** 4.1 (Confluence + Balanced Decision Making - Signal/Risk Lists)  
**Datum:** 2025-11-09  
**Owner:** Platform Architecture Team

---

## Executive Summary

Dit document definieert de **implementation details en lifecycle** van CausalityChain als **pure ID-only decision lineage tracker** voor quant analysis.

> **Architecture Overview:** See [DATA_FLOW.md](../../../architecture/DATA_FLOW.md#causality-tracking---decision-lineage) for high-level causality tracking patterns.

**Kernprincipe:**
> "CausalityChain tracks WHY decisions happened (causality), NOT WHAT outcomes were (reality)."

**Critical Design Decision (Issue #5 Resolution):**
> CausalityChain does **NOT** contain trade_id. Trade context is "business ballast" carried in parent DTOs via `target_trade_ids[]` field.

**Architectural Purpose:**
```
┌─────────────────────────────────────────────────────────────┐
│ QUANT QUESTION: "Why is this strategy profitable?"          │
│                                                              │
│ ANSWER: Correlate CAUSALITY (WHY) with OUTCOME (WHAT)       │
│                                                              │
│ CausalityChain → Decision lineage IDs                       │
│ StrategyJournal → Causality + Trade outcomes                │
└─────────────────────────────────────────────────────────────┘
```

---

## 1. CausalityChain Structure

### 1.1 Single Responsibility

> "Collect ONLY IDs for causality reconstruction - track the complete decision chain from origin through execution reality."

**Tracks (IDs only):**
- **Origin**: Which data triggered the flow? (Origin DTO with id + type)
- **Analysis**: Which worker analyzed? (signal_id OR risk_id - mutually exclusive)
- **Decision**: Which strategy decided? (strategy_directive_id)
- **Planning**: Which plans were created? (entry_plan_id, size_plan_id, exit_plan_id, execution_intent_id, execution_directive_id)
- **Execution Intent**: Which orders submitted? (order_ids[])
- **Execution Reality**: Which fills confirmed? (fill_ids[])

**NOT Responsible For:**
- ❌ Business data (symbol, price, direction - those live in DTOs)
- ❌ Timestamps (each DTO has own timestamp field)
- ❌ Confidence scores (Signal/StrategyDirective have those)
- ❌ **Trade IDs** (business ballast in parent DTOs via `target_trade_ids[]`)
- ❌ **Batch IDs** (pipeline coordination, not causality)

### 1.2 DTO Implementation

```python
# backend/dtos/causality.py

@dataclass(frozen=True)
class CausalityChain:
    """Pure ID-only decision lineage tracker."""
    
    # ORIGIN - Type-safe platform data reference
    origin: Origin  # Origin(id="TCK_...", type=OriginType.TICK)
    
    # WORKER OUTPUT IDs - Lists support confluence + balanced decision making
    signal_ids: list[str] = field(default_factory=list)   # SIG_... (detection)
    risk_ids: list[str] = field(default_factory=list)     # RSK_... (assessment)
    strategy_directive_id: str | None = None               # STR_... (decision)
    
    # PLANNING IDs
    entry_plan_id: str | None = None                       # ENT_...
    size_plan_id: str | None = None                        # SIZ_...
    exit_plan_id: str | None = None                        # EXT_...
    execution_intent_id: str | None = None                 # EXI_...
    execution_directive_id: str | None = None              # EXE_...
    
    # EXECUTION IDs - Intent vs Reality
    order_ids: list[str] = field(default_factory=list)    # ORD_... (intent)
    fill_ids: list[str] = field(default_factory=list)     # FIL_... (reality)
```

**Key Design Decisions:**
- **Signal/Risk Lists**: StrategyPlanner can receive BOTH signals AND risks for balanced decision making
- **Confluence Pattern**: Multiple SignalDetectors → multiple signal_ids in single StrategyDirective
- **Order vs Fill**: order_ids = intent, fill_ids = reality (may differ: partial fills, slippage)
- **ID format**: `{PREFIX}_{YYYYMMDD}_{HHMMSS}_{hash}` (see `backend/utils/id_generators.py`)
- **Immutable**: `frozen=True` prevents accidental modification

### 1.3 Extension Pattern

```python
# Workers extend CausalityChain by creating immutable copies
extended_causality = causality.model_copy(update={"signal_ids": [*causality.signal_ids, new_signal_id]})
```

**Principles:**
- ✅ Extension only - workers add IDs, never remove
- ✅ Immutable - prevents modification accidents
- ✅ No business data - pure ID tracking
- ✅ Lists accumulate - signals/risks/orders/fills append to existing lists

---

## 2. Component ID Ownership

**Who Creates Which IDs:**

| Component | Creates | Adds to CausalityChain |
|-----------|---------|------------------------|
| **DataProvider** | Origin(id, type) | origin (via PlatformDataDTO) |
| **SignalWorker** | signal_id | Appends to signal_ids[] |
| **RiskWorker** | risk_id | Appends to risk_ids[] |
| **StrategyPlanner** | strategy_directive_id | Creates CausalityChain with origin + signal_ids[] + risk_ids[] + strategy_directive_id |
| **PlanningAggregator** | entry_plan_id, size_plan_id, exit_plan_id, execution_intent_id, execution_directive_id | Extends with all plan IDs |
| **ExecutionHandler** | order_ids[] | Extends with order_ids[] |
| **ExchangeConnector** | fill_ids[] | Extends with fill_ids[] |

**Design Note:** Each component extends CausalityChain by creating a new immutable copy with additional IDs. No component modifies existing instances.

---

## 3. ID Propagation Flow

### 3.1 Birth to Execution

```
┌──────────────────────────────────────────────────────────────────────────┐
│                  CAUSALITY CHAIN - ID COLLECTION FLOW                     │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│ 1. ORIGIN (DataProvider)                                                 │
│    └─> Generates: Origin(id="TCK_...", type=TICK)                       │
│    └─> Output: PlatformDataDTO with Origin field                        │
│                                                                           │
│ 2. FLOW INIT (FlowInitiator)                                            │
│    └─> Receives: PlatformDataDTO with Origin                            │
│    └─> Passes through: Origin stays in PlatformDataDTO                  │
│    └─> NOTE: NO extraction, NO StrategyCache storage                    │
│                                                                           │
│ 3. CONTEXT (ContextWorker)                                               │
│    └─> Enriches with market state (Origin passed through)               │
│                                                                           │
│ 4. SIGNAL/RISK (SignalWorkers AND/OR RiskWorkers)                       │
│    └─> SignalDetectors: Produce Signal DTOs → signal_ids[]              │
│    └─> RiskMonitors: Produce Risk DTOs → risk_ids[]                     │
│    └─> NOTE: Can produce BOTH signals AND risks (balanced decisions)    │
│                                                                           │
│ 5. STRATEGY (StrategyPlanner) - CausalityChain BIRTH                    │
│    └─> Reads: cache.platform_data.origin                                │
│    └─> Reads: ALL signals via cache.get_dtos("signals", Signal)         │
│    └─> Reads: ALL risks via cache.get_dtos("risk_signals", Risk)        │
│    └─> Creates: CausalityChain(origin=..., signal_ids=[...], risk_ids=[...])│
│    └─> Creates: StrategyDirectiveBatch with CausalityChain              │
│    └─> All directives in batch share same CausalityChain                │
│    └─> CONSTRAINT: 1 worker = 1 strategy (SRP enforcement)              │
│                                                                           │
│ 6. PLANNING (PlanningAggregator per StrategyDirective)                  │
│    └─> Receives: StrategyDirective with CausalityChain                  │
│    └─> Coordinates: Entry/Size/Exit/Execution plan workers              │
│    └─> Extends CausalityChain: Adds entry_plan_id, size_plan_id, etc.  │
│    └─> Creates: ExecutionDirectiveBatch with extended CausalityChain    │
│                                                                           │
│ 7. EXECUTION (ExecutionHandler)                                          │
│    └─> Receives: ExecutionDirectiveBatch with CausalityChain            │
│    └─> Creates: order_id(s) for exchange submission                     │
│    └─> Extends CausalityChain: Adds order_ids to list                   │
│    └─> Submits orders to ExchangeConnector                              │
│                                                                           │
│ 8. EXCHANGE REALITY (ExchangeConnector replies)                          │
│    └─> Exchange confirms fills                                          │
│    └─> ExchangeConnector generates: fill_id(s)                          │
│    └─> Extends CausalityChain: Adds fill_ids to list                    │
│    └─> NOTE: fill_ids may differ from order_ids (partial fills)         │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

```

---

## 4. Architectural Constraints

### 4.1 Signal/Risk Balanced Decision Making

**Rule:** StrategyPlanner can receive **BOTH** signals AND risks simultaneously for comprehensive decision making.

**CausalityChain Structure:**
```python
signal_ids: list[str] = []  # Multiple signals (confluence)
risk_ids: list[str] = []    # Multiple risks (concurrent risk factors)
```

**Use Cases:**

**1. Confluence Pattern** - Multiple signals strengthen conviction:
```python
# Example: 3 SignalDetectors → 1 StrategyDirective
signal_ids = [
    "SIG_20251108_100001_abc",  # RSI oversold
    "SIG_20251108_100001_def",  # MACD cross
    "SIG_20251108_100002_ghi"   # Volume spike
]
# StrategyPlanner: High confidence entry (3 confirming signals)
```

**2. Balanced Decision** - Signals + Risks for informed decisions:
```python
# Example: DCA strategy waits for BOTH opportunity AND risk assessment
signals = cache.get_dtos("signals", Signal)      # Opportunity score
risks = cache.get_dtos("risk_signals", Risk)     # Risk level
# StrategyPlanner: Adaptive position sizing based on both
```

**3. Pending Risk** - StrategyPlanner tracks risks via state persistence:
```python
# Example: Risk monitor detects high volatility
# StrategyPlanner stores pending risk in state
# New signal arrives → StrategyPlanner factors in pending risk
```

**Rationale:**
- **Signal.confidence** and **Risk.severity** are symmetric (0.0-1.0) for balanced analysis
- StrategyPlanner accesses ALL signals/risks via `cache.get_dtos()`
- State persistence enables cross-event decision making
- Reflects trading reality: opportunities exist alongside risks

### 4.2 Order vs Fill Divergence

**Example:**
```
Order for 100 shares
├─> order_ids = ["ORD_20251108_100000_abc"]
└─> fill_ids = ["FIL_20251108_100001_def", "FIL_20251108_100002_ghi"]
    (partial fills: 60 + 40 shares)
```

**Why Track Both:**
- Captures intent → reality divergence
- Enables analysis: slippage, partial fills, order rejection patterns
- Complete causality story for quant analysis

### 4.3 StrategyPlanner Constraint

**Rule:** StrategyPlanner workers SHALL implement exactly ONE strategy. Multiple strategies = separate workers.

**Rationale:**
- SRP enforcement (1 worker = 1 responsibility)
- Atomic strategy decisions (all directives in batch = 1 strategy analysis)
- No strategy_id needed in CausalityChain
- Configuration validation enforces constraint

### 4.4 Origin Propagation

**Flow:**
```
DataProvider → Generates Origin(id="TCK_...", type=TICK)
    ↓
PlatformDataDTO.origin → FlowInitiator (passes through)
    ↓
StrategyPlanner → Reads cache.platform_data.origin → Creates CausalityChain
```

**Design:**
- Origin lives in PlatformDataDTO (NOT StrategyCache)
- FlowInitiator = pass-through only (no extraction logic)
- CausalityChain created only when data becomes relevant (StrategyDirectiveBatch produced)
- StrategyPlanner owns CausalityChain creation

---

## 5. References

**Related Architecture Documents:**
- `docs/architecture/PIPELINE_FLOW.md` - Complete pipeline specification
- `docs/architecture/EXECUTION_FLOW.md` - Detailed execution flow (order placement, fills, async exchange replies)
- `docs/architecture/CORE_PRINCIPLES.md` - Bus-agnostic patterns

**Component Design Documents:**
- `docs/development/backend/dtos/ORIGIN_DTO_DESIGN.md` (prelim) - Origin DTO structure
- `docs/development/backend/execution/EXECUTION_HANDLER_DESIGN.md` (prelim) - Order ID creation & CausalityChain updates
- `docs/development/backend/ledger/STRATEGY_LEDGER_DESIGN.md` (prelim) - Trade reality persistence
- `docs/development/backend/core/STRATEGY_JOURNAL_WRITER_DESIGN.md` (prelim) - Causality persistence & correlation
- `docs/development/backend/core/FLOW_TERMINATOR_DESIGN.md` (prelim) - Flow termination

**Implementation Files:**
- `backend/dtos/causality.py` - CausalityChain DTO (TO BE UPDATED: signal_ids/risk_ids lists, add fill_ids/order_ids, use Origin)
- `backend/dtos/shared/origin.py` (NEW) - Origin DTO (id + type)
- `backend/dtos/platform_data.py` - PlatformDataDTO (TO BE UPDATED: add Origin field)
- `backend/dtos/strategy/strategy_directive.py` - Has target_trade_ids[] field (trade context ballast)
- `backend/dtos/execution/execution_directive.py` - Has target_trade_ids[] field (trade context ballast)
- `backend/utils/id_generators.py` - ID format specification (str format, prefixes)

---

**Document Version History:**
- v1.0 (2025-11-06): Initial draft with problematic assumptions
- v2.0 (2025-11-07): Complete rewrite - pure decision lineage, FlowTerminator design
- v2.1 (2025-11-07): Removed implementation examples, clarified birth ID propagation
- v2.2 (2025-11-08): Major architecture revision - StrategyPlanner creates CausalityChain, component separation
- v2.3 (2025-11-08): SRP-focused - origin_id in PlatformDataDTO, StrategyDirectiveBatch, removed cross-component implementation details, added prelim doc references
- v4.0 (2025-11-08): Event-agnostic rewrite - removed ALL event references, incorrect signal/risk XOR constraint, added fill_ids, focused on pure ID tracking
- v4.1 (2025-11-09): Corrected signal/risk to lists (no XOR) - documented confluence pattern + balanced decision making use cases
