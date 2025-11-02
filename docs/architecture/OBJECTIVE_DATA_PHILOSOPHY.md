# Objective Data Philosophy - The "Quant Leap"

**Status:** Architecture Foundation  
**Last Updated:** 2025-11-02

---

## Executive Summary

S1mpleTraderV3 implements a **pure objective data model** where ContextWorkers produce facts without interpretation, and consumers (SignalDetectors, RiskMonitors, StrategyPlanners) apply their own subjective logic. This enables contradictory strategies to coexist using the same objective data.

**The Core Principle:**
> ContextWorkers are **objective data providers**, not opinion givers. The full responsibility for interpretation lies with the consuming workers.

**Why "Quant Leap"?**  
This architecture shift makes the platform fundamentally more flexible and "quant-friendly" by separating objective market facts from subjective trading logic.

---

## The Three Architectural Principles

### 1. ContextWorkers = Objective Fact Producers

**What they do:**
- Calculate technical indicators (EMA, RSI, Bollinger Bands)
- Detect market structure (support/resistance, chart patterns)
- Classify market regimes (trending, ranging, volatile)
- Transform statistical data (z-scores, percentiles)

**What they DON'T do:**
- ❌ NO subjective labels ("bullish", "bearish", "strong", "weak")
- ❌ NO SWOT classification ("Strength", "Weakness")  
- ❌ NO aggregation into scores or assessments
- ❌ NO interpretation of their own output

**Output Pattern:**
```python
class EMADetector(StandardWorker):
    def process(self) -> DispositionEnvelope:
        # OBJECTIVE FACT - just a number
        ema_20 = df['close'].ewm(span=20).mean().iloc[-1]
        
        # Store to TickCache WITHOUT interpretation
        self.strategy_cache.set_result_dto(
            self,
            EMAOutputDTO(ema_20=ema_20)  # Just the fact: 50100.50
        )
        
        return DispositionEnvelope(disposition="CONTINUE")
```

**Key Insight:**  
The EMA detector has **no opinion** about whether `ema_20=50100.50` is good or bad. It's simply a fact about the market at this point in time.

---

### 2. Consumers = Subjective Interpreters

**Who consumes:**
- SignalDetectors
- RiskMonitors
- StrategyPlanners

**What they do:**
- Read objective facts from TickCache
- Apply their **own**, **plugin-specific** interpretation logic
- Publish subjective signals/decisions to EventBus

**Example 1: Trend-Following Strategy**
```python
class TrendFollowingSignal(StandardWorker):
    def process(self) -> DispositionEnvelope:
        # 1. Get OBJECTIVE facts
        dtos = self.strategy_cache.get_required_dtos(self)
        ema_data = dtos[EMAOutputDTO]
        price = self.strategy_cache.get_base_context().current_price
        
        # 2. Apply SUBJECTIVE interpretation
        if price > ema_data.ema_20:
            # MY logic: price above EMA = signal
            return DispositionEnvelope(
                disposition="PUBLISH",
                event_payload=Signal(confidence=0.7)
            )
        
        return DispositionEnvelope(disposition="CONTINUE")
```

**Example 2: Mean-Reversion Strategy (Contradictory!)**
```python
class MeanReversionSignal(StandardWorker):
    def process(self) -> DispositionEnvelope:
        # 1. Get SAME objective facts
        dtos = self.strategy_cache.get_required_dtos(self)
        ema_data = dtos[EMAOutputDTO]
        price = self.strategy_cache.get_base_context().current_price
        
        distance = (price - ema_data.ema_20) / ema_data.ema_20
        
        # 2. Apply OPPOSITE subjective interpretation
        if distance > 0.05:  # 5% above EMA
            # MY logic: price too far above EMA = overbought = signal to short
            return DispositionEnvelope(
                disposition="PUBLISH",
                event_payload=Signal(
                    direction="short",
                    confidence=0.8
                )
            )
        
        return DispositionEnvelope(disposition="CONTINUE")
```

**Key Insight:**  
Two strategies consume the **same objective fact** (`ema_20=50100.50`) and reach **opposite conclusions**. This is the power of separating facts from interpretation.

---

### 3. Taxonomy = Descriptive Labels, Not Contracts

**The `type` field (ENFORCED):**
- Defines the worker's **architectural role**
- Determines output contracts (what can be produced)
- Validated by platform during bootstrap

**The `subtype` field (NOT ENFORCED):**
- Purely **descriptive label** (tag)
- Used for documentation, filtering, UI grouping
- Platform **ignores** subtypes during execution
- No architectural impact

**Example:**
```yaml
# Plugin A
identification:
  type: "context_worker"  # ENFORCED: Can only write to TickCache
  subtype: "indicator_calculation"  # TAG: Documentation/filtering

# Plugin B
identification:
  type: "context_worker"  # ENFORCED: Can only write to TickCache
  subtype: "structural_analysis"  # TAG: Documentation/filtering
```

**Architecturally identical:** Both can only `set_result_dto()` to TickCache. Neither can publish to EventBus. The subtype just helps humans categorize plugins.

---

## Data Flow: Facts → Interpretation

### The TickCache as "Objective Reality"

After the ContextWorker chain completes, the TickCache contains a **map of objective facts** about the market:

```python
TickCache = {
    EMAOutputDTO: EMAOutputDTO(ema_20=50100.50, ema_50=49800.30),
    RSIOutputDTO: RSIOutputDTO(rsi=65.3),
    MarketStructureDTO: MarketStructureDTO(
        high=51000.00,
        low=49500.00,
        structure_type="BULLISH_BOS"
    ),
    VolumeProfileDTO: VolumeProfileDTO(
        volume_at_price={50000: 1500, 50100: 2000, ...}
    )
}
```

**This is NOT:**
- ❌ An assessment ("market is strong")
- ❌ A recommendation ("should buy")
- ❌ A SWOT classification ("Strength: trend alignment")

**This IS:**
- ✅ Pure, objective market data
- ✅ Context-free facts
- ✅ Foundation for ANY interpretation

### Consumers Apply Subjective Lenses

Different strategies look at this **same objective reality** and make different decisions:

**Trend Follower:**
- Sees: `price > ema_20` and `structure_type="BULLISH_BOS"`
- Interprets: "Bullish trend confirmed, signal to long"
- Action: Publishes `Signal(direction="long")`

**Mean Reverter:**
- Sees: `rsi=65.3` and `price 5% above ema_20`
- Interprets: "Overbought, likely pullback, signal to short"
- Action: Publishes `Signal(direction="short")`

**Volatility Trader:**
- Sees: `volume_at_price` distribution and `high-low range`
- Interprets: "Low volatility, avoid trading"
- Action: Returns `DispositionEnvelope(disposition="STOP")`

**All three consume the same TickCache, none conflict, each applies own logic.**

---

## Removed Components (Architecture Simplification)

### What Was Removed

1. **`ContextFactor` DTO** (28 tests)
   - **Was:** Individual SWOT factor with strength/weakness label
   - **Why removed:** ContextWorkers no longer make subjective assessments

2. **`AggregatedContextAssessment` DTO** (14 tests)
   - **Was:** Platform-aggregated strengths and weaknesses
   - **Why removed:** No SWOT aggregation layer

3. **`FactorRegistry` (backend/core/context_factors.py)** (20 tests)
   - **Was:** Registry for managing ContextFactor types
   - **Why removed:** No ContextFactor DTOs to register

4. **`ContextAggregator` (Platform Component)**
   - **Was:** Collected ContextFactors and aggregated into assessment
   - **Why removed:** No aggregation needed - consumers read TickCache directly

**Total:** 62 tests removed, architecture simplified

### What Replaced Them

**Nothing!** That's the point. The complexity was unnecessary.

**Before (V2 SWOT model):**
```
ContextWorker → ContextFactor("TRENDING_REGIME", polarity="strength")
   ↓
ContextAggregator → AggregatedContextAssessment(strengths=[...], weaknesses=[...])
   ↓
SignalDetector → Reads aggregated assessment
```

**After (V3 Objective model):**
```
ContextWorker → RegimeOutputDTO(regime="TRENDING")
   ↓
SignalDetector → Reads TickCache, interprets regime as signal
```

**Eliminated:** 2 DTOs, 1 platform component, 62 tests, entire aggregation layer.

---

## Benefits of Objective Data Philosophy

### 1. Flexibility
- ✅ Multiple strategies can coexist with contradictory interpretations
- ✅ Easy to add new strategies without platform changes
- ✅ Strategies don't interfere with each other

### 2. Testability
- ✅ ContextWorkers test pure calculations (deterministic)
- ✅ Consumers test interpretation logic in isolation
- ✅ Mock TickCache with known objective facts

### 3. Clarity
- ✅ Clear separation: facts vs opinions
- ✅ No hidden aggregation logic
- ✅ Easier to debug (inspect TickCache = see all facts)

### 4. Quant-Friendly
- ✅ Perfect for quantitative strategies (backtest many interpretations)
- ✅ No platform bias (no hardcoded SWOT logic)
- ✅ Data-driven (optimize parameters, not platform code)

### 5. Simplicity
- ✅ Removed 62 tests, still 100% coverage
- ✅ Fewer components, less complexity
- ✅ Easier onboarding for new developers

---

## Comparison: SWOT Model vs Objective Model

| Aspect | SWOT Model (V2) | Objective Model (V3) |
|--------|----------------|---------------------|
| **ContextWorker Output** | `ContextFactor(type="TRENDING", polarity="strength")` | `RegimeOutputDTO(regime="TRENDING")` |
| **Interpretation** | Platform (ContextAggregator) | Consumer (SignalDetector) |
| **Aggregation** | Platform component required | None - direct TickCache access |
| **Flexibility** | Limited (platform defines SWOT) | Unlimited (consumers define logic) |
| **Contradictory Strategies** | Difficult (fight over SWOT labels) | Easy (different interpretations coexist) |
| **Test Count** | 404 tests | 362 tests (-10% complexity) |
| **DTOs** | 14 (2 for SWOT) | 12 (SWOT removed) |
| **Platform Components** | ContextAggregator + PlanningAggregator | PlanningAggregator only |

---

## Implementation Checklist

When creating a new ContextWorker:

- [ ] Produces objective DTOs only (e.g., `EMAOutputDTO(ema_20=value)`)
- [ ] No subjective labels ("bullish", "strong", etc.)
- [ ] No interpretation in docstrings ("signals potential entry")
- [ ] DTO fields are measurements, not opinions
- [ ] Uses `set_result_dto()` to store to TickCache
- [ ] **NEVER** publishes to EventBus

When creating a new SignalDetector/RiskMonitor:

- [ ] Reads objective facts from TickCache via `get_required_dtos()`
- [ ] Applies own interpretation logic (documented in worker)
- [ ] Publishes subjective signal to EventBus
- [ ] Interpretation logic is isolated (doesn't affect other workers)
- [ ] Can coexist with contradictory interpretations

---

## See Also

- [Core Principles](CORE_PRINCIPLES.md) - Plugin First, Separation of Concerns
- [Worker Taxonomy](WORKER_TAXONOMY.md) - Worker categories and type vs subtype
- [Data Flow](DATA_FLOW.md) - TickCache and EventBus communication
- [Point-in-Time Model](POINT_IN_TIME_MODEL.md) - DTO-centric architecture

---

**Last Updated:** 2025-11-02  
**Document Status:** Architecture Foundation  
**Related Decision:** Sessie Overdracht - De "Quant Leap" Architectuur (2025-11-01)
