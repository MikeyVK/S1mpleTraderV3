# Terminology Review - Quant Refactoring

**Date:** 2025-11-02  
**Status:** ✅ APPROVED - Ready for implementation

## APPROVED DECISIONS

1. DTO Names: **Signal** / **Risk** (not MarketSignal/RiskEvent)
2. Worker Names: **SignalDetector** / **RiskMonitor**
3. ID Prefixes: **SIG_** / **RSK_**
4. Field Names: **signal_ids** / **risk_ids** (in CausalityChain)
5. Field Names: **signal_id** / **risk_id** (in DTOs)
6. Enum Names: **SignalType** / **RiskType**
7. File Names: **signal.py** / **risk.py**
8. Keep: **ContextWorker** (no rename needed)

---

## Proposed Changes

### 1. Signal Detection DTOs

#### Option A: MarketSignal (PROPOSED)
```python
class MarketSignal(BaseModel):
    """Represents a detected market signal for entry/exit opportunities."""
    signal_id: str = Field(description="Signal ID (SIG_...)")
```

**Rationale:**
- ✅ Clear: "Market" indicates it's about market conditions
- ✅ Accurate: "Signal" is standard quant terminology
- ✅ Flexible: Can represent bullish/bearish/neutral signals
- ⚠️ Slightly generic - doesn't indicate direction

#### Option B: TradingSignal
```python
class TradingSignal(BaseModel):
    """Represents a detected trading signal."""
    signal_id: str
```

**Rationale:**
- ✅ More specific than "Market"
- ✅ Standard in trading systems
- ⚠️ Might imply already executable (vs. requiring planning)

#### Option C: EntrySignal / ExitSignal (split)
```python
class EntrySignal(BaseModel): ...
class ExitSignal(BaseModel): ...
```

**Rationale:**
- ✅ Very explicit about intent
- ❌ Requires two DTOs instead of one
- ❌ OpportunitySignal currently handles both entry AND exit

**QUESTION 1:** Prefer MarketSignal, TradingSignal, or split Entry/Exit?

---

### 2. Risk Monitoring DTOs

#### Option A: RiskEvent (PROPOSED)
```python
class RiskEvent(BaseModel):
    """Represents a detected risk event requiring position adjustment."""
    risk_event_id: str = Field(description="Risk event ID (RSK_...)")
```

**Rationale:**
- ✅ Standard risk management terminology
- ✅ "Event" indicates discrete occurrence
- ✅ Clear distinction from signals (risk vs. opportunity)

#### Option B: RiskAlert
```python
class RiskAlert(BaseModel):
    """Risk alert notification."""
    alert_id: str
```

**Rationale:**
- ✅ Emphasizes notification aspect
- ⚠️ "Alert" might sound less critical than "Event"

#### Option C: RiskTrigger
```python
class RiskTrigger(BaseModel):
    """Risk condition trigger."""
    trigger_id: str
```

**Rationale:**
- ✅ Indicates causality (trigger → action)
- ⚠️ Might confuse with EventBus triggers

**QUESTION 2:** Prefer RiskEvent, RiskAlert, or RiskTrigger?

---

### 3. Worker Categories

#### Proposed Names:
| Current | Proposed | Alternative |
|---------|----------|-------------|
| `OpportunityWorker` | `SignalWorker` | `SignalDetector`, `PatternWorker` |
| `ThreatWorker` | `RiskMonitor` | `RiskWorker`, `GuardWorker` |

**SignalWorker Rationale:**
- ✅ Parallel to "MarketSignal" output
- ✅ Generic enough for any signal type
- ⚠️ Might be too generic

**Alternative: SignalDetector**
- ✅ More explicit about function
- ✅ Common in signal processing
- ⚠️ Longer name

**RiskMonitor Rationale:**
- ✅ "Monitor" indicates continuous watching
- ✅ Distinct from "Worker" pattern
- ✅ Standard in risk management systems

**QUESTION 3:** Worker naming preferences?

---

### 4. ID Prefixes

#### Proposed Prefixes:
| Current | Proposed | Alternative | Notes |
|---------|----------|-------------|-------|
| `OPP_` | `SIG_` | `MKT_`, `TRD_` | Signal ID |
| `THR_` | `RSK_` | `ALT_`, `EVT_` | Risk event ID |

**SIG_ Rationale:**
- ✅ Short, memorable
- ✅ Aligns with "Signal"
- ✅ Common abbreviation

**Alternative: MKT_** (Market)
- ✅ More specific
- ⚠️ Might imply market data vs. derived signal

**Alternative: TRD_** (Trade)
- ⚠️ Confusing - not yet a trade

**RSK_ Rationale:**
- ✅ Clear abbreviation of "Risk"
- ✅ Parallel to SIG_
- ✅ Three letters (consistent)

**Alternative: ALT_** (Alert)
- ⚠️ Not standard abbreviation

**Alternative: EVT_** (Event)
- ✅ Generic, accurate
- ⚠️ Could confuse with system events

**QUESTION 4:** ID prefix preferences?

---

### 5. Field Names in CausalityChain

#### Proposed:
```python
class CausalityChain(BaseModel):
    # Birth IDs
    tick_id: str | None = None
    news_id: str | None = None
    schedule_id: str | None = None
    
    # Signal/Risk tracking
    market_signal_ids: list[str] = Field(default_factory=list)
    risk_event_ids: list[str] = Field(default_factory=list)
    
    # Planning pipeline
    strategy_directive_id: str | None = None
    entry_plan_id: str | None = None
    # ... etc
```

**Alternative field names:**
- `signal_ids` (shorter, but loses "market" context)
- `trading_signal_ids` (longer, more specific)
- `entry_signal_ids` + `exit_signal_ids` (split, more work)

**QUESTION 5:** Field naming in CausalityChain?

---

### 6. Enum Names

#### Proposed:
```python
class SignalType(str, Enum):
    """Market signal classification."""
    MOMENTUM_BREAKOUT = "MOMENTUM_BREAKOUT"
    MEAN_REVERSION = "MEAN_REVERSION"
    VOLUME_SURGE = "VOLUME_SURGE"
    # ... etc

class RiskEventType(str, Enum):
    """Risk event classification."""
    DRAWDOWN_LIMIT = "DRAWDOWN_LIMIT"
    VOLATILITY_SPIKE = "VOLATILITY_SPIKE"
    CORRELATION_BREAK = "CORRELATION_BREAK"
    # ... etc
```

**Alternative enum names:**
- `MarketSignalType` (more explicit)
- `TradingSignalType` (trading-specific)
- `RiskAlertType` (if we use RiskAlert)

**QUESTION 6:** Enum naming preferences?

---

## Consistency Analysis

### Current Naming Pattern
```
Worker Category → Output DTO → ID Prefix
ContextWorker   → ??? (removed) → (none)
OpportunityWorker → OpportunitySignal → OPP_
ThreatWorker    → ThreatSignal → THR_
PlanningWorker  → StrategyDirective → STR_
```

### Proposed Pattern A (Parallel Structure)
```
Worker Category → Output DTO → ID Prefix
SignalWorker    → MarketSignal → SIG_
RiskMonitor     → RiskEvent    → RSK_
StrategyPlanner → StrategyDirective → STR_
```

### Proposed Pattern B (Aligned Naming)
```
Worker Category   → Output DTO      → ID Prefix
SignalDetector    → MarketSignal    → SIG_
RiskMonitor       → RiskEvent       → RSK_
StrategyPlanner   → StrategyDirective → STR_
```

**QUESTION 7:** Prefer Pattern A or B for Worker naming?

---

## Domain-Specific Considerations

### Quantitative Finance Terminology

**Standard Terms:**
- ✅ "Signal" - widely used (buy/sell signals, alpha signals)
- ✅ "Risk Event" - standard in risk management
- ✅ "Market Signal" - common in algo trading
- ⚠️ "Opportunity" - more business/SWOT than quant
- ⚠️ "Threat" - more business/SWOT than quant

**Industry Examples:**
- QuantConnect: `Signal`, `Alpha`, `Insight`
- Zipline: `Signal`, `Order`
- Backtrader: `Signal`, `Indicator`
- Proprietary systems: Often use "Signal" + "Risk"

**QUESTION 8:** Any other quant terminology we should consider?

---

## Migration Considerations

### Files Requiring Rename
**Backend:**
1. `backend/dtos/strategy/opportunity_signal.py` → `market_signal.py`
2. `backend/dtos/strategy/threat_signal.py` → `risk_event.py`

**Tests:**
3. `tests/unit/dtos/strategy/test_opportunity_signal.py` → `test_market_signal.py`
4. `tests/unit/dtos/strategy/test_threat_signal.py` → `test_risk_event.py`

**Documentation:**
5. `docs/reference/dtos/opportunity_signal.md` → `market_signal.md`
6. Create: `docs/reference/dtos/risk_event.md`

**QUESTION 9:** Any concerns about file renames?

---

## Potential Issues

### 1. Semantic Ambiguity
**Concern:** "MarketSignal" could be confused with raw market data
**Mitigation:** Clear docstrings emphasizing "derived/analyzed signal"

### 2. Entry vs. Exit Signals
**Concern:** OpportunitySignal currently handles both entry AND exit logic
**Current behavior:** 
- Entry: `direction="BUY"` or `direction="SELL"` (opening position)
- Exit: Triggered by RiskEvent, not OpportunitySignal

**Proposed:** Keep unified `MarketSignal` - direction field handles both cases

**QUESTION 10:** Should we split Entry/Exit into separate DTOs?

### 3. Worker Taxonomy Impact
**Concern:** Changing worker names affects WORKER_TAXONOMY.md structure
**Impact:** Need to update 5-category framework documentation

**Current categories:**
1. ContextWorker
2. OpportunityWorker ← RENAME
3. ThreatWorker ← RENAME
4. PlanningWorker
5. ExecutionWorker

**Proposed categories:**
1. ContextWorker (or rename to DataWorker?)
2. SignalWorker
3. RiskMonitor
4. StrategyPlanner
5. ExecutionWorker

**QUESTION 11:** Should we also rename ContextWorker to something clearer?

---

## Summary of Open Questions

1. DTO Name: MarketSignal vs. TradingSignal vs. split Entry/Exit?
2. Risk DTO: RiskEvent vs. RiskAlert vs. RiskTrigger?
3. Worker Names: SignalWorker vs. SignalDetector? RiskMonitor vs. RiskWorker?
4. ID Prefixes: SIG/RSK vs. MKT/RSK vs. TRD/ALT?
5. Field Names: market_signal_ids vs. signal_ids vs. trading_signal_ids?
6. Enum Names: SignalType vs. MarketSignalType vs. TradingSignalType?
7. Worker Pattern: Keep "Worker" suffix or use "Detector/Monitor/Planner"?
8. Other quant terminology to consider?
9. File rename concerns?
10. Split Entry/Exit DTOs or keep unified?
11. Rename ContextWorker as well?

---

## Recommended Decisions (My Preference)

| # | Question | Recommendation | Reason |
|---|----------|----------------|--------|
| 1 | DTO Name | **MarketSignal** | Standard, flexible, clear |
| 2 | Risk DTO | **RiskEvent** | Standard risk mgmt term, accurate |
| 3 | Workers | **SignalWorker** / **RiskMonitor** | Parallel, distinctive |
| 4 | Prefixes | **SIG_** / **RSK_** | Short, clear, consistent |
| 5 | Fields | **market_signal_ids** / **risk_event_ids** | Explicit, searchable |
| 6 | Enums | **SignalType** / **RiskEventType** | Concise, clear |
| 7 | Pattern | Keep "Worker" suffix | Consistency with existing |
| 8 | Other terms | None - keep it simple | - |
| 9 | Renames | Proceed as planned | Clear mapping |
| 10 | Split DTOs | **No** - keep unified | YAGNI principle |
| 11 | ContextWorker | **No** - separate refactor | Scope creep |

---

## Next Steps

1. **Review & Approve** - Your feedback on above questions
2. **Finalize Terminology** - Lock in decisions
3. **Update REFACTORING_LOG.md** - Document approved terms
4. **Execute Phase 2** - Begin backend refactoring

---

**Status:** ⏸️ PAUSED - Awaiting terminology approval
