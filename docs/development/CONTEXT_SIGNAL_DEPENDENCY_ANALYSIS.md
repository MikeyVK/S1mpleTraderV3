# Context → Signal Dependencies: Grondige Analyse

**Status:** Design Analysis  
**Datum:** 2025-10-28  
**Doel:** In kaart brengen van data dependencies tussen ContextWorkers en Opportunity/ThreatWorkers

---

## Executive Summary

Deze analyse onderzoekt **WAT** Opportunity/ThreatWorkers precies nodig hebben van ContextWorkers om hun signaal detectie te kunnen uitvoeren. We focussen op de **tweede primaire rol** van ContextWorkers: het leveren van **actionable input** voor de detectiefase.

**Kernvraag:** Welke context data is **essentieel** voor elke type signaaldetectie?

---

## 1. Worker Taxonomie Overzicht

### 1.1 ContextWorker Subtypes (7)

| Subtype | Primaire Output | Doel |
|---------|----------------|------|
| **REGIME_CLASSIFICATION** | MarketRegimeDTO | Trending/Ranging classificatie |
| **STRUCTURAL_ANALYSIS** | MarketStructureDTO | BOS, ChoCH, swing points, liquidity zones |
| **INDICATOR_CALCULATION** | IndicatorOutputDTO | EMA, RSI, MACD, ATR, Bollinger Bands |
| **MICROSTRUCTURE_ANALYSIS** | OrderbookDataDTO | Orderbook imbalance, bid/ask spread |
| **TEMPORAL_CONTEXT** | SessionInfoDTO | Sessions (London, NY), killzones |
| **SENTIMENT_ENRICHMENT** | SentimentScoreDTO | News sentiment, social media buzz |
| **FUNDAMENTAL_ENRICHMENT** | FundamentalDataDTO | On-chain metrics, earnings data |

### 1.2 OpportunityWorker Subtypes (7)

| Subtype | Detectie Focus | Typische Signal Types |
|---------|----------------|----------------------|
| **TECHNICAL_PATTERN** | Chart patronen | FVG, breakout, divergence, engulfing |
| **MOMENTUM_SIGNAL** | Trend sterkte | Trend continuation, momentum burst |
| **MEAN_REVERSION** | Overbought/oversold | Range reversion, oversold bounce |
| **STATISTICAL_ARBITRAGE** | Correlatie deviaties | Pair divergence, spread compression |
| **EVENT_DRIVEN** | News events | News reaction, earnings surprise |
| **SENTIMENT_SIGNAL** | Extreme sentiment | Extreme fear entry, euphoria exit |
| **ML_PREDICTION** | Model voorspellingen | ML predicted move, pattern probability |

### 1.3 ThreatWorker Subtypes (5)

| Subtype | Monitoring Focus | Typische Threat Types |
|---------|------------------|----------------------|
| **PORTFOLIO_RISK** | Portfolio metrics | Max drawdown, over-exposure, correlation risk |
| **MARKET_RISK** | Markt condities | Volatility spike, liquidity drought |
| **SYSTEM_HEALTH** | Technische status | Connection lost, data gap, feed delay |
| **STRATEGY_PERFORMANCE** | Performance metrics | Win rate decline, profit factor drop |
| **EXTERNAL_EVENT** | Externe factoren | High impact news, regulatory change |

---

## 2. Dependency Matrix: Opportunity Workers

### 2.1 TECHNICAL_PATTERN (FVG, Breakouts, Divergences)

**Detectie Logica:**
- **FVG:** 3-candle gap waar candle 2 volledig binnen candle 1 en 3 ligt
- **Breakout:** Prijs breekt key structure level met volume bevestiging
- **Divergence:** Price makes new high/low maar indicator niet

**CRITICAL Dependencies (Kan NIET zonder):**

| Context DTO | Velden | Rationale |
|-------------|--------|-----------|
| **MarketStructureDTO** | swing_highs, swing_lows, liquidity_zones, order_blocks | Identificatie van breakout levels, FVG zones |
| **IndicatorOutputDTO** (RSI/MACD) | rsi_14, macd_line, macd_histogram | Divergence detectie (price vs indicator) |
| **OHLCV Data** (via IOhlcvProvider) | open, high, low, close, volume | Candle patterns, gap identificatie |

**OPTIONAL Dependencies (Verhogen confidence):**

| Context DTO | Velden | Benefit |
|-------------|--------|---------|
| **MarketRegimeDTO** | regime, strength | Breakouts in trending regime = hoger succes |
| **OrderbookDataDTO** | imbalance_ratio | Bevestigt liquiditeit voor breakout |
| **IndicatorOutputDTO** (ATR) | atr_14 | Volatility context voor pattern sizing |

**Voorbeeld Gebruik:**
```python
# FVGDetector (OpportunityWorker)
def process(self) -> DispositionEnvelope:
    # Critical data
    required_dtos = self.context_provider.get_required_dtos(self)
    structure = required_dtos[MarketStructureDTO]
    ohlcv = self.ohlcv_provider.get_window(...)
    
    # Optional enhancers
    regime = required_dtos.get(MarketRegimeDTO)  # May be None
    
    # FVG detection
    for i in range(len(ohlcv) - 3):
        if self._is_fvg(ohlcv, i):
            # Check if FVG aligns with liquidity zone
            if self._near_liquidity_zone(ohlcv.iloc[i], structure.liquidity_zones):
                confidence = 0.75
                
                # Boost confidence if trending regime
                if regime and regime.regime == "trending":
                    confidence += 0.10
                
                signal = OpportunitySignal(
                    signal_type="fvg_entry",
                    confidence=confidence,
                    # ...
                )
```

---

### 2.2 MOMENTUM_SIGNAL (Trend Continuation)

**Detectie Logica:**
- Prijs in established trend + momentum indicator bevestiging
- Pullback naar moving average + bounce
- Volume surge in trend direction

**CRITICAL Dependencies:**

| Context DTO | Velden | Rationale |
|-------------|--------|-----------|
| **MarketRegimeDTO** | regime, strength | MOET trending zijn (anders geen momentum) |
| **IndicatorOutputDTO** (EMA) | ema_20, ema_50, ema_200 | Trend richting en pullback levels |
| **IndicatorOutputDTO** (MACD/RSI) | macd_histogram, rsi_14 | Momentum bevestiging |
| **OHLCV Data** | close, volume | Price action en volume surge |

**OPTIONAL Dependencies:**

| Context DTO | Velden | Benefit |
|-------------|--------|---------|
| **MarketStructureDTO** | swing_lows (in uptrend) | Higher-low confirmatie |
| **SessionInfoDTO** | session, is_killzone | Timing validation (NY open = volume) |

**Voorbeeld Afhankelijkheid:**
```python
# MomentumContinuation (OpportunityWorker)
_required_dto_types = [
    MarketRegimeDTO,      # CRITICAL: moet trending zijn
    EMAOutputDTO,         # CRITICAL: trend direction
    MACDOutputDTO,        # CRITICAL: momentum confirmation
]

def process(self):
    dtos = self.context_provider.get_required_dtos(self)
    regime = dtos[MarketRegimeDTO]
    ema = dtos[EMAOutputDTO]
    macd = dtos[MACDOutputDTO]
    
    # Gate: Only detect in trending regime
    if regime.regime != "trending" or regime.strength < 0.6:
        return DispositionEnvelope(disposition="STOP")
    
    # Trend direction from EMAs
    trend_up = ema.ema_20 > ema.ema_50 > ema.ema_200
    
    # Momentum confirmation
    if trend_up and macd.macd_histogram > 0:
        # Detect continuation opportunity
        ...
```

---

### 2.3 MEAN_REVERSION (Oversold/Overbought Bounces)

**Detectie Logica:**
- Prijs in ranging market + extreme RSI/Bollinger
- Price touch support/resistance + reversal candle
- Bollinger squeeze → expansion

**CRITICAL Dependencies:**

| Context DTO | Velden | Rationale |
|-------------|--------|-----------|
| **MarketRegimeDTO** | regime | MOET ranging zijn (trend = no reversion) |
| **IndicatorOutputDTO** (RSI) | rsi_14 | Overbought (>70) / Oversold (<30) |
| **IndicatorOutputDTO** (Bollinger) | bb_upper, bb_lower, bb_middle | Mean en extremes |
| **OHLCV Data** | close, high, low | Price positioning vs bands |

**OPTIONAL Dependencies:**

| Context DTO | Velden | Benefit |
|-------------|--------|---------|
| **MarketStructureDTO** | liquidity_zones | Support/resistance levels |
| **IndicatorOutputDTO** (ATR) | atr_14 | Volatility context voor target sizing |

---

### 2.4 STATISTICAL_ARBITRAGE (Pair Trading)

**Detectie Logica:**
- Spread tussen correlated assets deviates > threshold
- Z-score van spread > 2 of < -2
- Correlation breakdown detectie

**CRITICAL Dependencies:**

| Context DTO | Velden | Rationale |
|-------------|--------|-----------|
| **Multi-Asset OHLCV** | close prices (asset A & B) | Spread calculation |
| **IndicatorOutputDTO** (Custom: SpreadDTO) | spread, z_score, correlation | Statistical metrics |

**OPTIONAL Dependencies:**

| Context DTO | Velden | Benefit |
|-------------|--------|---------|
| **MarketRegimeDTO** (beide assets) | regime | Verify both assets in similar regime |
| **FundamentalDataDTO** | Sector data | Fundamental link validation |

**Note:** Dit type vereist **multi-asset support** in TickCache!

---

### 2.5 EVENT_DRIVEN (News Reactions)

**Detectie Logica:**
- High-impact news event published
- Price gap or volume spike post-news
- Sentiment shift detectie

**CRITICAL Dependencies:**

| Context DTO | Velden | Rationale |
|-------------|--------|-----------|
| **SentimentScoreDTO** | source, score, event_type | News trigger identificatie |
| **OHLCV Data** | volume, close | Volume spike en price movement |

**OPTIONAL Dependencies:**

| Context DTO | Velden | Benefit |
|-------------|--------|---------|
| **MarketStructureDTO** | liquidity_zones | Pre-news positioning levels |
| **IndicatorOutputDTO** (ATR) | atr_14 | Expected volatility post-news |
| **SessionInfoDTO** | session | News impact varies per session |

---

### 2.6 SENTIMENT_SIGNAL (Extreme Fear/Greed)

**Detectie Logica:**
- Sentiment indicator reaches extreme (e.g., Fear & Greed < 20)
- Contrarian entry: buy fear, sell greed
- Social media buzz analysis

**CRITICAL Dependencies:**

| Context DTO | Velden | Rationale |
|-------------|--------|-----------|
| **SentimentScoreDTO** | score, source | Primary signal trigger |

**OPTIONAL Dependencies:**

| Context DTO | Velden | Benefit |
|-------------|--------|---------|
| **IndicatorOutputDTO** (RSI) | rsi_14 | Technical confirmation (oversold + fear = strong) |
| **MarketStructureDTO** | key support levels | Entry near structure = better R/R |
| **FundamentalDataDTO** | on_chain_metrics | Crypto: whale activity confirmation |

---

### 2.7 ML_PREDICTION (Model-Based Signals)

**Detectie Logica:**
- ML model predicts price movement
- Feature vector van market state → model → probability
- Threshold-based signal generation

**CRITICAL Dependencies:**

| Context DTO | Velden | Rationale |
|-------------|--------|-----------|
| **ALL Context DTOs** | (varies by model) | Model features (regime, indicators, structure, sentiment) |

**OPTIONAL Dependencies:**
- N/A (model bepaalt welke features critical zijn)

**Feature Engineering Pattern:**
```python
# MLPredictionWorker
def _build_feature_vector(self):
    dtos = self.context_provider.get_required_dtos(self)
    
    # Model requires: regime, 3 EMAs, RSI, MACD, structure metrics
    regime = dtos[MarketRegimeDTO]
    ema = dtos[EMAOutputDTO]
    rsi = dtos[RSIOutputDTO]
    macd = dtos[MACDOutputDTO]
    structure = dtos[MarketStructureDTO]
    
    features = np.array([
        1.0 if regime.regime == "trending" else 0.0,
        regime.strength,
        ema.ema_20, ema.ema_50, ema.ema_200,
        rsi.rsi_14,
        macd.macd_line, macd.signal_line,
        len(structure.liquidity_zones),
        # ... 20+ more features
    ])
    
    return features
```

---

## 3. Dependency Matrix: Threat Workers

### 3.1 PORTFOLIO_RISK (Drawdown, Exposure)

**Monitoring Logica:**
- Current drawdown vs max_drawdown_threshold
- Total exposure vs max_exposure_limit
- Correlation risk across positions

**CRITICAL Dependencies:**

| Data Source | Type | Rationale |
|-------------|------|-----------|
| **ILedgerProvider** | Platform Provider | Real-time portfolio state |
| **StrategyLedger** | Platform Data | Position sizes, PnL, equity curve |

**OPTIONAL Context Dependencies:**

| Context DTO | Velden | Benefit |
|-------------|--------|---------|
| **IndicatorOutputDTO** (ATR) | atr_14 | Volatility-adjusted position sizing |
| **MarketRegimeDTO** | regime | Reduce exposure in ranging = lower edge |

**Note:** ThreatWorkers gebruiken vaak **GEEN** context DTOs, maar **platform providers** (Ledger, Journal)!

---

### 3.2 MARKET_RISK (Volatility, Liquidity)

**Monitoring Logica:**
- ATR spike > 2x average
- Bid/ask spread widening
- Volume drought detectie

**CRITICAL Dependencies:**

| Context DTO | Velden | Rationale |
|-------------|--------|-----------|
| **IndicatorOutputDTO** (ATR) | atr_14, atr_sma_14 | Volatility spike detection |
| **OrderbookDataDTO** | bid_ask_spread, order_depth | Liquidity monitoring |
| **OHLCV Data** | volume | Volume drought detection |

**OPTIONAL Dependencies:**

| Context DTO | Velden | Benefit |
|-------------|--------|---------|
| **SessionInfoDTO** | session | Expected volatility per session |

---

### 3.3 SYSTEM_HEALTH (Connection, Data Integrity)

**Monitoring Logica:**
- Websocket connection status
- Data feed latency monitoring
- Missing candle detection

**CRITICAL Dependencies:**

| Data Source | Type | Rationale |
|-------------|------|-----------|
| **IDataFeedProvider** | Platform Provider | Connection status, latency metrics |
| **Metadata** | System info | Last tick timestamp, sequence numbers |

**OPTIONAL Context Dependencies:**
- **None** (system health is independent van market context)

---

### 3.4 STRATEGY_PERFORMANCE (Win Rate, Profit Factor)

**Monitoring Logica:**
- Rolling win rate < threshold
- Profit factor declining trend
- Max consecutive losses breached

**CRITICAL Dependencies:**

| Data Source | Type | Rationale |
|-------------|------|-----------|
| **IJournalReader** | Platform Provider | Historical trade results |
| **StrategyJournal** | Platform Data | Win/loss history, PnL per trade |

**OPTIONAL Context Dependencies:**

| Context DTO | Velden | Benefit |
|-------------|--------|---------|
| **MarketRegimeDTO** | regime | Segment performance by regime type |

---

### 3.5 EXTERNAL_EVENT (News, Regulatory)

**Monitoring Logica:**
- High-impact news event detected
- Regulatory announcement parsed
- Black swan event classification

**CRITICAL Dependencies:**

| Context DTO | Velden | Rationale |
|-------------|--------|-----------|
| **SentimentScoreDTO** | event_type, severity, source | External event trigger |

**OPTIONAL Dependencies:**

| Context DTO | Velden | Benefit |
|-------------|--------|---------|
| **SessionInfoDTO** | session | Event impact timing analysis |

---

## 4. Synthesized Dependency Patterns

### 4.1 Most Common Context Dependencies (Top 5)

| Context DTO | Used By (Opportunity) | Used By (Threat) | Total |
|-------------|----------------------|------------------|-------|
| **MarketRegimeDTO** | 5/7 workers | 1/5 workers | **85% coverage** |
| **IndicatorOutputDTO** (EMA, RSI, MACD, ATR) | 6/7 workers | 2/5 workers | **83% coverage** |
| **MarketStructureDTO** | 4/7 workers | 0/5 workers | **33% coverage** |
| **OHLCV Data** (via Provider) | 7/7 workers | 1/5 workers | **67% coverage** |
| **SentimentScoreDTO** | 2/7 workers | 1/5 workers | **25% coverage** |

**Interpretation:**
- **MarketRegimeDTO** is near-universal for opportunity detection
- **Indicators** (EMA, RSI, MACD, ATR) are critical for most strategies
- **Structure** matters for technical pattern strategies
- **Threat workers** depend more on **platform providers** than context

### 4.2 Critical vs Optional Pattern

**Critical Dependencies:**
- **OpportunityWorkers:** 60% hebben 3-5 critical context DTOs
- **ThreatWorkers:** 60% hebben 0-1 critical context DTOs (rest is platform data)

**Optional Dependencies:**
- Used for **confidence boosting** (niet blocking)
- Typical boost: +0.10 to +0.20 confidence
- Examples: Regime confirmation, volume validation, session timing

---

## 5. Tick Cache Implications

### 5.1 Cache Content Per Tick (Typical Strategy)

**Minimale Cache (Simple Strategy):**
```python
{
    MarketRegimeDTO: <instance>,
    EMAOutputDTO: <instance>,
    RSIOutputDTO: <instance>,
    MACDOutputDTO: <instance>,
}
```
**Size:** ~4 DTOs × 2KB = **8KB per tick**

**Uitgebreide Cache (Complex Strategy):**
```python
{
    # Context outputs (7 potential DTOs)
    MarketRegimeDTO: <instance>,
    MarketStructureDTO: <instance>,
    EMAOutputDTO: <instance>,
    RSIOutputDTO: <instance>,
    MACDOutputDTO: <instance>,
    ATROutputDTO: <instance>,
    BollingerBandDTO: <instance>,
    OrderbookDataDTO: <instance>,
    SessionInfoDTO: <instance>,
    SentimentScoreDTO: <instance>,
    
    # Intermediate results (signal phase)
    PatternConfirmationDTO: <instance>,
    VolumeSpikeDTO: <instance>,
}
```
**Size:** ~12 DTOs × 2KB = **24KB per tick**

### 5.2 Cache Lifetime Pattern

```
RAW_TICK event
    ↓
TickCacheManager: create_cache()
    ↓
CONTEXT PHASE (Sequential)
    ↓ MarketStructureDetector → MarketStructureDTO → cache
    ↓ EMADetector → EMAOutputDTO → cache
    ↓ RegimeClassifier → MarketRegimeDTO → cache
    ↓ (7 context workers max)
    ↓
SIGNAL PHASE (Parallel)
    ↓ FVGDetector reads: [MarketStructureDTO, EMAOutputDTO]
    ↓ MomentumSignal reads: [MarketRegimeDTO, EMAOutputDTO, MACDOutputDTO]
    ↓ (7 opportunity workers parallel)
    ↓
PLANNING PHASE
    ↓ (reads opportunity signals + context for validation)
    ↓
TICK_FLOW_COMPLETE
    ↓
TickCacheManager: clear_cache()
```

**Key Observation:** Context DTOs are **write-once** (by context workers), **read-many** (by signal workers).

---

## 6. Design Recommendations

### 6.1 ContextWorker Output Strategy

**Granularity Decision:**

**Option A: One DTO per Worker (Current)**
- `EMADetector` → `EMAOutputDTO(ema_20, ema_50, ema_200)`
- `RSIDetector` → `RSIOutputDTO(rsi_14)`
- `MACDDetector` → `MACDOutputDTO(macd_line, signal_line, histogram)`

**Pros:**
✅ Clear ownership (1 worker = 1 DTO)
✅ Easy dependency declaration (`requires_dtos: ["EMAOutputDTO"]`)
✅ Modular (enable/disable workers independently)

**Cons:**
❌ More DTOs in cache (12+ for complex strategy)
❌ More imports for consuming workers

**Option B: Grouped DTOs**
- `IndicatorSuite` → `AllIndicatorsDTO(ema, rsi, macd, atr, bollinger)`

**Pros:**
✅ Fewer cache entries
✅ Single import for consumers

**Cons:**
❌ Coupled workers (must run all indicators)
❌ Harder to test in isolation
❌ Loss of granular dependency control

**RECOMMENDATION:** **Option A** (One DTO per Worker)
- Aligns with SRP
- Supports modular strategy composition
- Cache size is negligible (24KB max)

---

### 6.2 Optional Dependencies Pattern

**Problem:** How do workers handle optional context?

**Solution 1: Explicit Optional Fetching**
```python
# Worker declares ONLY critical deps in manifest
manifest.requires_dtos: ["MarketRegimeDTO", "EMAOutputDTO"]

# In process():
required = self.context_provider.get_required_dtos(self)  # Must exist
regime = required[MarketRegimeDTO]
ema = required[EMAOutputDTO]

# Optional fetch (may return None)
optional_dtos = self.context_provider.get_required_dtos(
    self, 
    dto_types=[ATROutputDTO]  # Explicit optional request
)
atr = optional_dtos.get(ATROutputDTO)  # May be None

if atr and atr.atr_14 > threshold:
    confidence += 0.10  # Boost
```

**Solution 2: has_dto() Check**
```python
if self.context_provider.has_dto(ATROutputDTO):
    dtos = self.context_provider.get_required_dtos(self, [ATROutputDTO])
    atr = dtos[ATROutputDTO]
    # Use atr...
```

**RECOMMENDATION:** **Solution 2** (has_dto() check)
- More explicit intent
- Avoids exception handling for optional data
- Clearer code flow

---

### 6.3 Multi-Asset Support

**Challenge:** Statistical arbitrage needs data from **multiple assets**.

**Current Design:**
- `ITradingContextProvider` is tick-scoped
- Tick = single asset context

**Required Extension:**
```python
class ITradingContextProvider(Protocol):
    def get_base_context(self, asset: str | None = None) -> BaseContextDTO:
        """
        Get base context for specific asset.
        
        Args:
            asset: Asset symbol (e.g., "BTCUSDT"). 
                   If None, uses primary asset.
        """
        ...
    
    def get_required_dtos(
        self,
        requesting_worker: IWorker,
        dto_types: list[Type[BaseModel]] | None = None,
        asset: str | None = None  # NEW: asset filter
    ) -> Dict[Type[BaseModel], BaseModel]:
        """Get DTOs for specific asset."""
        ...
```

**Cache Structure (Multi-Asset):**
```python
# Option A: Flat with asset prefix
{
    (EMAOutputDTO, "BTCUSDT"): <instance>,
    (EMAOutputDTO, "ETHUSDT"): <instance>,
    (MarketRegimeDTO, "BTCUSDT"): <instance>,
}

# Option B: Nested by asset
{
    "BTCUSDT": {
        EMAOutputDTO: <instance>,
        MarketRegimeDTO: <instance>,
    },
    "ETHUSDT": {
        EMAOutputDTO: <instance>,
    }
}
```

**RECOMMENDATION:** **Option B** (Nested by asset) ✅ CONFIRMED
- Cleaner separation
- Easier to clear single asset  
- Natural grouping for multi-timeframe strategies
- **Use Case**: Confluence analysis (niet HFT arbitrage)
  - Example: BTC structuur + ETH momentum + altcoin sentiment → portfolio signal
  - Multi-asset data beschikbaar binnen zelfde tick voor cross-asset analysis

---

## 7. Design Decisions Summary

### 7.1 Dependency Declaration in Manifest ✅ RESOLVED

**Current (V2 Addendum):**
```yaml
# manifest.yaml
requires_dtos:
  - "EMAOutputDTO"
  - "MarketRegimeDTO"
```

**Question:** Hoe specificeren we **optionals**?

**Option A: Separate Lists**
```yaml
requires_dtos:
  critical:
    - "EMAOutputDTO"
    - "MarketRegimeDTO"
  optional:
    - "ATROutputDTO"
    - "SessionInfoDTO"
```

**Option B: Annotation**
```yaml
requires_dtos:
  - name: "EMAOutputDTO"
    required: true
  - name: "MarketRegimeDTO"
    required: true
  - name: "ATROutputDTO"
    required: false
```

**RECOMMENDATION:** **Option B** (Annotation) ✅ CONFIRMED
- **Rationale**:
  - **Extensible**: Makkelijk uitbreiden met metadata (versioning, fallback strategies)
  - **Consistency**: Zelfde pattern als andere configs (alles is key-value objects)
  - **Pydantic-friendly**: Direct mappable naar typed config classes
  - **Future-proof**: Ruimte voor `min_version`, `fallback_to`, `confidence_weight`, etc.

**Final Syntax:**
```yaml
# manifest.yaml
requires_dtos:
  - name: "EMAOutputDTO"
    required: true
    # Future: min_version: "2.0.0", fallback_to: "SMAOutputDTO"
  - name: "MarketRegimeDTO"
    required: true
  - name: "ATROutputDTO"
    required: false  # Boosts confidence +15% if available
```

---

### 7.2 Context Phase Sequencing ✅ RESOLVED

- **Beslissing**: **Intra-context dependencies ESSENTIEEL**
- **Evidence**: ICT/SMC strategy uit V2 Architecture (zie §3.6.1):
  ```yaml
  context_workers:
    # Sequential structural analysis chain
    - market_structure_detector    # 1. Detecteert BOS/CHoCH
    - liquidity_zone_mapper         # 2. Gebruikt MarketStructureDTO
    - order_block_identifier        # 3. Gebruikt Structure + Liquidity
    - premium_discount_calculator   # 4. Gebruikt structure levels voor Fib zones
    
    # Can run parallel with structure chain
    - session_analyzer              # Independent (temporal)
    
    # Requires ALL previous context
    - higher_timeframe_bias         # 5. Synthesizes ALL context voor regime
  ```

- **Sequencing Strategy** (uit **Addendum 5.1: Expliciet Bedraad Netwerk**):
  - `wiring_map.yaml` definieert expliciete source→target relaties
  - `base_wiring.yaml` bevat category-level templates
  - `strategy_wiring_map.yaml` (UI-generated) specificeert instance-level dependencies
  - Platform orkestreert via `EventAdapter` per worker

- **Implementation Pattern**:
  ```yaml
  # strategy_wiring_map.yaml (generated by Strategy Builder UI)
  wiring_rules:
    - wiring_id: "structure_to_liquidity"
      source:
        component_id: "market_structure_detector_001"
        event_name: "ContextOutput"
      target:
        component_id: "liquidity_zone_mapper_001"
        handler_method: "process"
    
    - wiring_id: "structure_and_liquidity_to_orderblock"
      source:
        component_id: "liquidity_zone_mapper_001"
        event_name: "ContextOutput"
      target:
        component_id: "order_block_identifier_001"
        handler_method: "process"
  ```

- **Manifest Extension** (needed):
  ```yaml
  # manifest.yaml voor order_block_identifier plugin
  requires_context_dtos:  # NEW field for intra-context deps
    critical:
      - "MarketStructureDTO"
      - "LiquidityZonesDTO"
  
  requires_platform_providers:  # Existing field
    - "IOhlcvProvider"
  ```

- **Performance Consideration**: 
  - Independent workers (session_analyzer) kunnen **parallel** draaien
  - Dependent chains moeten **serieel** (maar chains zelf parallel met elkaar)
  - Platform orkestratie via `wiring_map` → **geen hardcoded logic in TickCacheManager**
  - Strategy Builder UI genereert correcte wiring op basis van plugin manifesten

---

### 7.3 Dependency Metadata Journaling ✅ RESOLVED

- **Beslissing**: **NIET NODIG**
- **Rationale**: Strategy config wordt al gelogd per run
  - Config bevat volledige `requires_dtos` declaraties uit manifesten
  - Config bevat `strategy_wiring_map` (welke dependencies actief waren)
  - Config bevat worker params
  - Bij post-mortem analyse: koppel results aan strategy_config
- **Voordeel**: Geen extra runtime overhead, config is single source of truth
- **Implicatie**: Manifesten + strategy_config = complete dependency audit trail

---

### 7.4 DTO Versioning & Breaking Changes

**Question:** Wat als `EMAOutputDTO` structure wijzigt (v1 → v2)?

**Scenario:**
```python
# v1
class EMAOutputDTO(BaseModel):
    ema_20: Decimal
    ema_50: Decimal

# v2 (breaking change)
class EMAOutputDTO(BaseModel):
    emas: Dict[int, Decimal]  # {20: ..., 50: ..., 200: ...}
```

**Impact:**
- Consuming workers **breken** (expect `ema_20` field)
- Manifest validation **detecteert type**, maar niet structure

**Mitigation Options:**

**Option A: Semantic Versioning in Paths**
```python
# Producer v2
from backend.dto_reg.s1mple/ema_detector/v2_0_0/ema_output_dto import EMAOutputDTO

# Consumer still on v1
from backend.dto_reg.s1mple/ema_detector/v1_0_0/ema_output_dto import EMAOutputDTO
```
→ Allows **gradual migration**

**Option B: DTO Adapters**
```python
class EMAOutputDTOAdapter:
    @staticmethod
    def v1_to_v2(v1: EMAOutputDTOv1) -> EMAOutputDTOv2:
        return EMAOutputDTOv2(
            emas={20: v1.ema_20, 50: v1.ema_50}
        )
```
→ Platform handles conversion transparently

**RECOMMENDATION:** **Option A** (Versioned Paths) + deprecation warnings
- Explicit about versioning
- No magic conversion overhead
- Forces intentional upgrades

---

## 8. Conclusies & Next Steps

### 8.1 Key Findings

1. **MarketRegimeDTO + Indicators = Universal Foundation**
   - 85% van opportunity workers needs regime classification
   - EMA, RSI, MACD, ATR zijn top-4 indicators

2. **ThreatWorkers zijn Platform-Centric**
   - 60% gebruikt GEEN context DTOs
   - Primair ILedgerProvider, IJournalReader
   - Context DTOs alleen voor market risk monitoring

3. **Tick Cache is Lightweight**
   - Typical: 8KB (simple) to 24KB (complex)
   - Write-once, read-many pattern
   - Sub-second lifetime

4. **Optional Dependencies = Confidence Boosters**
   - +10-20% confidence bump
   - Non-blocking (graceful degradation)
   - Examples: session timing, volume validation

### 8.2 Design Decisions FINALIZED

✅ **One DTO per ContextWorker** (granular, modular)  
✅ **Option B (Annotation syntax)** for manifest requires_dtos (extensible, Pydantic-friendly)  
✅ **Intra-context dependencies SUPPORTED** via `requires_context_dtos` manifest field  
✅ **has_dto() pattern** for optional fetching (graceful degradation)  
✅ **Nested cache structure** for multi-asset (Dict[asset, Dict[Type, DTO]])  
✅ **Multi-asset for confluence analysis** (NOT HFT arbitrage)  
✅ **NO dependency metadata journaling** (strategy config already logged)  
✅ **Versioned DTO paths** for breaking changes (semantic versioning)  

### 8.3 Implementation Action Items (from User Feedback)

#### ✅ ACTION 1: Update ITradingContextProvider for Multi-Asset
**Status**: Design ready (see §6.4)  
**Implementation**: Week 2
```python
# Add asset parameter to all methods
def get_base_context(self, asset: str | None = None) -> BaseContextDTO: ...
def get_required_dtos(..., asset: str | None = None) -> Dict[Type, DTO]: ...
```

#### ❌ ACTION 2: Create manifest_schema.py (SKIP FOR NOW)
**User Feedback**: "Mogelijk moeten we zelfs kiezen voor manifest_schema_categorie.py"
- Different worker categories may need specific manifest configs
- This is "onderbuikgevoel", not confirmed requirement
- **Decision**: DEFER until we have more worker categories implemented
- **Alternative**: Start with simple WorkerManifest Pydantic class, evolve as needed

#### ❌ ACTION 3: No Manifest Validation Tool Yet (SKIP)
**User Feedback**: "Ook niet doen, dit is onderdeel van de plugin ontwikkeling"
- Validation is part of plugin development workflow
- **Decision**: Focus on interface contracts ONLY
- Platform injects interfaces, plugins implement them

#### ❌ ACTION 4: No Initial Context DTOs Yet (SKIP)
**User Feedback**: Implicit (focus on interface, not implementations)
- DTO creation is plugin development task
- **Decision**: Design MarketRegimeDTO, EMAOutputDTO, etc. AS EXAMPLES in docs
- **Don't implement** until we have actual ContextWorker plugins

### 8.4 Revised Roadmap (Post User Feedback)

**Week 1: Interface & Core Types**
1. Finalize `ITradingContextProvider` interface
2. Define `BaseContextDTO` structure
3. Create initial DTO types:
   - `MarketRegimeDTO`
### 8.4 Revised Roadmap (Post User Feedback)

**FOCUS**: Interface contracts ONLY, not implementations

**Week 1-2: Core Platform Interfaces**
1. ✅ ITradingContextProvider protocol (DONE - see ITRADINGCONTEXTPROVIDER_DESIGN.md)
2. ✅ BaseContextDTO (DONE - timestamp + current_price)
3. 🔄 Update ITradingContextProvider for multi-asset support
   - Add `asset: str | None` parameter to methods
   - Document nested cache structure
4. Create IWorkerLifecycle protocol (bootstrap, process, cleanup)
5. Create IEventBus protocol (publish, subscribe patterns)
6. Update WorkerManifest Pydantic schema:
   ```python
   class DTORequirement(BaseModel):
       name: str  # "EMAOutputDTO"
       required: bool
       # Future: min_version, fallback_to
   
   class WorkerManifest(BaseModel):
       requires_dtos: list[DTORequirement]
       requires_context_dtos: list[DTORequirement]  # NEW: intra-context deps
       requires_platform_providers: list[str]
   ```

**Week 3-4: Base Worker Classes**
1. BaseWorker abstract class
2. ContextWorker, OpportunityWorker, ThreatWorker (category-specific ABCs)
3. Integration points with ITradingContextProvider
4. Exception types (MissingContextDataError, InvalidDTOError)

**DEFER tot Plugin Development Phase:**
- ❌ Concrete DTO implementations (MarketRegimeDTO, etc.)
- ❌ Concrete worker implementations (EMADetector, etc.)
- ❌ Manifest validation tooling
- ❌ manifest_schema_categorie.py (evolve as needed)

---

**Document Owner:** Architecture Team  
**Status:** ✅ Decisions Finalized - Ready for Implementation  
**Last Updated:** 2025-10-28
