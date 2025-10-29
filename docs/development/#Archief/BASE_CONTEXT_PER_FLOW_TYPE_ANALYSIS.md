# BaseContextDTO per Flow Type - Analysis

**Status:** Design Analysis  
**Datum:** 2025-10-28  
**Gerelateerd aan:** ITradingContextProvider Design - Open Question #4

---

## Executive Summary

**Kernvraag:** "Een run wordt niet altijd getriggerd door een market tick - zie birth IDs in causality chain. Ieder type run heeft mogelijk zijn eigen base data."

**Drie Flow Types (uit CausalityChain):**
1. **Market Tick Flow** → `tick_id` (RAW_TICK event)
2. **News Event Flow** → `news_id` (NEWS_RECEIVED event)  
3. **Schedule Event Flow** → `schedule_id` (SCHEDULED_TASK event)

**Bevindingen:**
- Elke flow type heeft **ANDERE base data beschikbaar**
- `current_price` is NIET altijd beschikbaar (schedule/news zonder tick)
- BaseContextDTO moet **flow-type agnostic** zijn
- Verschillende flows vereisen **verschillende provider capabilities**

---

## 1. Flow Type Inventarisatie

### 1.1 Market Tick Flow (RAW_TICK)

**Birth ID:** `tick_id` (e.g., "TIK_20251028_143000_a1b2c3d4")

**Trigger Event:**
```python
# EventBus receives from market data feed
RAW_TICK {
    "timestamp": datetime(2025, 10, 28, 14, 30, 0),
    "asset": "BTCUSDT",
    "price": Decimal("67500.00"),
    "volume": Decimal("15.23"),
    "tick_id": "TIK_20251028_143000_a1b2c3d4"
}
```

**TickCacheManager Processing:**
```python
def _handle_raw_tick(self, event: RawTickEvent):
    cache = {}  # Fresh cache
    
    context_provider.start_new_tick(
        tick_cache=cache,
        timestamp=event.timestamp,
        current_price=event.price,  # ✅ AVAILABLE
        asset=event.asset
    )
    
    # Publish TICK_FLOW_START for workers
```

**Available Data:**
- ✅ `timestamp` - Exact moment of tick
- ✅ `current_price` - Last trade price
- ✅ `asset` - Symbol being traded
- ✅ OHLCV data (via IOhlcvProvider up to timestamp)
- ✅ Order book data (via IDepthProvider at timestamp)

**Typical Workers Involved:**
- ContextWorkers: EMADetector, RSICalculator, MarketStructureDetector
- OpportunityWorkers: FVGDetector, MomentumSignal, TechnicalPattern
- ThreatWorkers: MarketRiskMonitor (volatility spikes)

**Use Case:** Standard trading flow - detect opportunities from market movement

---

### 1.2 News Event Flow (NEWS_RECEIVED)

**Birth ID:** `news_id` (e.g., "NWS_20251027_143000_k7l8m9n0")

**Trigger Event:**
```python
# EventBus receives from news feed adapter
NEWS_RECEIVED {
    "timestamp": datetime(2025, 10, 27, 14, 30, 0),  # News publish time
    "news_id": "NWS_20251027_143000_k7l8m9n0",
    "headline": "Fed announces rate cut",
    "sentiment": "bullish",
    "impact_level": "high",
    "affected_assets": ["BTCUSDT", "ETHUSDT"],
    
    # NO price field! News event heeft geen tick price.
}
```

**TickCacheManager Processing:**
```python
def _handle_news_received(self, event: NewsReceivedEvent):
    cache = {}  # Fresh cache
    
    # ❌ NO current_price available from news event!
    # Must fetch latest price from market data provider
    
    latest_price = self._market_data.get_latest_price(
        asset=event.affected_assets[0],  # Primary asset
        as_of=event.timestamp
    )
    
    context_provider.start_new_tick(
        tick_cache=cache,
        timestamp=event.timestamp,
        current_price=latest_price,  # ⚠️ DERIVED, not from trigger event
        asset=event.affected_assets[0]
    )
```

**Available Data:**
- ✅ `timestamp` - News publish time
- ⚠️ `current_price` - DERIVED from market data (not part of trigger event!)
- ✅ `asset` - From affected_assets
- ✅ News metadata (sentiment, impact, headline)
- ❌ GEEN real-time tick data (event is async from market)
- ⚠️ OHLCV data (via provider, maar possibly stale - news kan out-of-market-hours zijn!)

**Typical Workers Involved:**
- ContextWorkers: SentimentAnalyzer (news-specific!)
- ThreatWorkers: ExternalEventMonitor, NewsImpactAssessor
- OpportunityWorkers: EventDrivenSignal (correlate news → market regime)

**Use Case Examples:**
1. **Threat Scenario:** "Fed emergency meeting → pause all trading"
   - ThreatWorker publishes CriticalEvent
   - ModifyDirective: EXIT all positions
   
2. **Opportunity Scenario:** "Positive regulatory news → bullish shift"
   - ContextWorker updates sentiment context
   - OpportunityWorker checks if aligns with technical setup

**Edge Case Problem:**
```python
# News arrives during market close (weekend/holiday)
NEWS_RECEIVED {
    "timestamp": datetime(2025, 10, 26, 10, 0, 0),  # Sunday 10:00
    "headline": "Breaking: Major partnership announced"
}

# ❌ get_latest_price() returns FRIDAY close price (stale!)
# Should we:
# A) Use stale price (Friday close)?
# B) Skip flow entirely (wait for market open)?
# C) Use price=None (optional field)?
```

---

### 1.3 Schedule Event Flow (SCHEDULED_TASK)

**Birth ID:** `schedule_id` (e.g., "SCH_20251028_080000_weekly_dca")

**Trigger Event:**
```python
# EventBus receives from Scheduler
SCHEDULED_TASK {
    "timestamp": datetime(2025, 10, 28, 8, 0, 0),  # Scheduled time
    "schedule_id": "SCH_20251028_080000_weekly_dca",
    "task_name": "weekly_dca_buy",
    "task_type": "DCA_PURCHASE",
    "params": {
        "asset": "BTCUSDT",
        "amount_usd": 100.0
    },
    
    # NO price field! Schedule event is time-based, not market-based.
}
```

**TickCacheManager Processing:**
```python
def _handle_scheduled_task(self, event: ScheduledTaskEvent):
    cache = {}  # Fresh cache
    
    # ❌ NO current_price in schedule event!
    # Must fetch from market data
    
    latest_price = self._market_data.get_latest_price(
        asset=event.params["asset"],
        as_of=event.timestamp
    )
    
    context_provider.start_new_tick(
        tick_cache=cache,
        timestamp=event.timestamp,
        current_price=latest_price,  # ⚠️ DERIVED
        asset=event.params["asset"]
    )
```

**Available Data:**
- ✅ `timestamp` - Scheduled execution time
- ⚠️ `current_price` - DERIVED from market data
- ✅ `asset` - From schedule params
- ✅ Schedule metadata (task_name, params)
- ❌ GEEN real-time tick data
- ⚠️ OHLCV data (via provider, but schedule kan out-of-market-hours zijn!)

**Typical Workers Involved:**
- ThreatWorkers: PortfolioRiskMonitor, DrawdownChecker
- PlanningWorkers: FixedRiskSizer (for DCA amount)
- ExecutionWorkers: MarketOrderRouter (for DCA execution)

**Use Case Examples:**
1. **Weekly DCA:** "Buy $100 of BTC every Monday 8:00 AM"
   - ContextWorkers: RegimeClassifier (is market in dip?)
   - ThreatWorkers: RiskAssessor (is portfolio overexposed?)
   - Planning: EntryPlanner (market order or limit?)
   
2. **Daily Rebalancing:** "Rebalance portfolio daily at 00:00"
   - ThreatWorkers: PortfolioRiskMonitor
   - Planning: Multi-asset rebalancing plans

**Edge Case Problem:**
```python
# Schedule fires during market close
SCHEDULED_TASK {
    "timestamp": datetime(2025, 10, 26, 8, 0, 0),  # Sunday (market closed!)
    "task_name": "weekly_dca_buy"
}

# ❌ get_latest_price() returns FRIDAY close (48 hours stale!)
# Options:
# A) Use stale price (inaccurate for DCA)
# B) Delay execution until market open
# C) Cancel this scheduled run
```

---

## 2. BaseContextDTO Design Problem

### 2.1 Current Design (Single-Purpose)

```python
class BaseContextDTO(BaseModel):
    """Minimale basis context voor een tick."""
    
    asset: str = Field(...)
    timestamp: datetime = Field(...)
    current_price: Decimal = Field(..., gt=0)  # ❌ REQUIRED!
    
    class Config:
        frozen = True
```

**Problemen:**
1. `current_price` is **NIET altijd beschikbaar** (news/schedule events)
2. `current_price` kan **stale** zijn (out-of-market-hours)
3. Field naam `current_price` impliceert **real-time tick price** (misleading voor schedule)
4. **Geen indicatie** van flow type (market/news/schedule)

---

### 2.2 Option A: Make current_price Optional

```python
class BaseContextDTO(BaseModel):
    """Minimale basis context voor een flow (tick/news/schedule)."""
    
    asset: str = Field(...)
    timestamp: datetime = Field(..., description="Flow trigger timestamp")
    
    current_price: Decimal | None = Field(
        default=None,
        gt=0,
        description=(
            "Latest market price at flow timestamp. "
            "Available for RAW_TICK flows. "
            "DERIVED (possibly stale) for NEWS/SCHEDULE flows. "
            "None if market closed or price unavailable."
        )
    )
    
    class Config:
        frozen = True
```

**Voordelen ✅:**
- Flexible - works for all flow types
- Honest about price availability
- Workers kunnen checken: `if ctx.current_price is not None`

**Nadelen ❌:**
- Workers die price nodig hebben moeten None-check doen
- Unclear wanneer price None is (market closed? error?)
- Geen metadata over price staleness

---

### 2.3 Option B: Add Flow Type Metadata

```python
from enum import Enum

class FlowType(str, Enum):
    """Type of strategy run trigger."""
    MARKET_TICK = "market_tick"       # Real-time market data
    NEWS_EVENT = "news_event"         # External news
    SCHEDULED_TASK = "scheduled_task" # Time-based trigger

class BaseContextDTO(BaseModel):
    """Minimale basis context voor een flow."""
    
    asset: str = Field(...)
    timestamp: datetime = Field(...)
    flow_type: FlowType = Field(..., description="What triggered this run")
    
    # Price metadata
    current_price: Decimal | None = Field(default=None, gt=0)
    price_source: str | None = Field(
        default=None,
        description="'tick' | 'derived' | None (if price unavailable)"
    )
    price_timestamp: datetime | None = Field(
        default=None,
        description="Timestamp of price data (may differ from flow timestamp)"
    )
    
    class Config:
        frozen = True
```

**Voordelen ✅:**
- Workers weten welk type flow ze verwerken
- Duidelijk of price real-time of stale is
- Enables flow-type-specific logic

**Nadelen ❌:**
- Complexer DTO (meer fields)
- Violates "minimal base context" principe
- Workers moeten meer metadata verwerken

---

### 2.4 Option C: Separate Base Context per Flow Type

```python
class BaseFlowContext(BaseModel):
    """Abstract base voor alle flow types."""
    asset: str
    timestamp: datetime
    
    class Config:
        frozen = True

class TickFlowContext(BaseFlowContext):
    """Context voor market tick flows."""
    current_price: Decimal = Field(..., gt=0)  # ✅ REQUIRED for ticks
    tick_id: str

class NewsFlowContext(BaseFlowContext):
    """Context voor news event flows."""
    current_price: Decimal | None = Field(default=None)  # Optional (derived)
    news_id: str
    headline: str
    sentiment: str

class ScheduleFlowContext(BaseFlowContext):
    """Context voor scheduled task flows."""
    current_price: Decimal | None = Field(default=None)  # Optional (derived)
    schedule_id: str
    task_name: str
```

**Voordelen ✅:**
- Type-safe per flow type
- Clear requirements per context type
- Flow-specific metadata included

**Nadelen ❌:**
- Workers moeten verschillende context types accepteren
- Provider interface wordt complex (multiple return types)
- Breaks "one BaseContextDTO" design

---

## 3. Worker Impact Analysis

### 3.1 Workers that REQUIRE current_price

**OpportunityWorkers:**
- MomentumSignal (price > EMA?)
- MeanReversion (distance from mean)
- TechnicalPattern (price break of structure)

**ThreatWorkers:**
- MarketRiskMonitor (volatility from price changes)
- StopLossCalculator (distance to stop)

**PlanningWorkers:**
- SizePlanner (position size based on price)
- EntryPlanner (limit order placement)

**Impact if current_price=None:**
```python
class MomentumSignal(OpportunityWorker):
    def process(self) -> DispositionEnvelope:
        ctx = self._context_provider.get_base_context()
        
        if ctx.current_price is None:
            # ❌ Cannot calculate momentum without price!
            return DispositionEnvelope(disposition="STOP", reason="No price data")
        
        # ... momentum calculation
```

---

### 3.2 Workers that DON'T need current_price

**ContextWorkers:**
- SentimentAnalyzer (only needs news data)
- SessionAnalyzer (only needs timestamp)
- FundamentalEnricher (uses external data)

**ThreatWorkers:**
- NewsImpactAssessor (evaluates news severity)
- ExternalEventMonitor (monitors events)

**Impact if current_price=None:**
```python
class SentimentAnalyzer(ContextWorker):
    def process(self) -> DispositionEnvelope:
        ctx = self._context_provider.get_base_context()
        
        # ✅ Price not needed - only timestamp for news correlation
        news_events = self._news_provider.get_recent_news(
            end_time=ctx.timestamp
        )
        
        sentiment = self._analyze(news_events)
        self._context_provider.set_result_dto(self, SentimentDTO(sentiment=sentiment))
```

---

## 4. Recommended Solution

### 4.1 Hybrid Approach: Optional Price + Flow Type Enum

```python
from enum import Enum
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field

class FlowTrigger(str, Enum):
    """What triggered this strategy run."""
    MARKET_TICK = "market_tick"
    NEWS_EVENT = "news_event"
    SCHEDULED_TASK = "scheduled_task"

class BaseContextDTO(BaseModel):
    """
    Minimale basis context voor een strategy run flow.
    
    Supports drie flow types:
    - MARKET_TICK: Real-time market data trigger
    - NEWS_EVENT: External news trigger
    - SCHEDULED_TASK: Time-based scheduled trigger
    
    Design:
    - timestamp: ALTIJD beschikbaar (flow trigger time)
    - asset: ALTIJD beschikbaar (from trigger event or config)
    - current_price: OPTIONEEL (only guaranteed for MARKET_TICK flows)
    - flow_trigger: Indicates what initiated this run
    """
    
    asset: str = Field(
        ...,
        description="Asset identifier (e.g., 'BTCUSDT')"
    )
    
    timestamp: datetime = Field(
        ...,
        description=(
            "Flow trigger timestamp (UTC). "
            "For MARKET_TICK: exact tick time. "
            "For NEWS_EVENT: news publish time. "
            "For SCHEDULED_TASK: scheduled execution time."
        )
    )
    
    flow_trigger: FlowTrigger = Field(
        ...,
        description="What triggered this strategy run"
    )
    
    current_price: Decimal | None = Field(
        default=None,
        gt=0,
        description=(
            "Latest known market price. "
            "MARKET_TICK: Real-time tick price (guaranteed). "
            "NEWS_EVENT/SCHEDULED_TASK: Derived from market data (may be stale or None). "
            "None if market closed or price unavailable."
        )
    )
    
    class Config:
        frozen = True
        
    # Helper methods
    def has_realtime_price(self) -> bool:
        """Check if current_price is real-time (from tick)."""
        return self.flow_trigger == FlowTrigger.MARKET_TICK and self.current_price is not None
    
    def has_derived_price(self) -> bool:
        """Check if current_price is derived (possibly stale)."""
        return (
            self.flow_trigger in [FlowTrigger.NEWS_EVENT, FlowTrigger.SCHEDULED_TASK]
            and self.current_price is not None
        )
```

### 4.2 TickCacheManager Implementation

```python
class TickCacheManager:
    """Manages tick cache lifecycle for all flow types."""
    
    def _handle_raw_tick(self, event: RawTickEvent):
        """Market tick flow - price guaranteed."""
        cache = {}
        self._context_provider.start_new_tick(
            tick_cache=cache,
            timestamp=event.timestamp,
            current_price=event.price,  # ✅ From tick
            asset=event.asset,
            flow_trigger=FlowTrigger.MARKET_TICK
        )
        self._publish_flow_start(cache, FlowTrigger.MARKET_TICK)
    
    def _handle_news_received(self, event: NewsReceivedEvent):
        """News event flow - price derived (best effort)."""
        cache = {}
        
        # Try to get latest price
        try:
            price = self._market_data.get_latest_price(
                asset=event.affected_assets[0],
                as_of=event.timestamp
            )
        except (MarketClosedError, PriceUnavailableError):
            price = None  # Accept None for news flows
        
        self._context_provider.start_new_tick(
            tick_cache=cache,
            timestamp=event.timestamp,
            current_price=price,  # ⚠️ May be None
            asset=event.affected_assets[0],
            flow_trigger=FlowTrigger.NEWS_EVENT
        )
        self._publish_flow_start(cache, FlowTrigger.NEWS_EVENT)
    
    def _handle_scheduled_task(self, event: ScheduledTaskEvent):
        """Schedule flow - price derived (best effort)."""
        cache = {}
        
        try:
            price = self._market_data.get_latest_price(
                asset=event.params["asset"],
                as_of=event.timestamp
            )
        except (MarketClosedError, PriceUnavailableError):
            price = None  # Accept None for schedule flows
        
        self._context_provider.start_new_tick(
            tick_cache=cache,
            timestamp=event.timestamp,
            current_price=price,  # ⚠️ May be None
            asset=event.params["asset"],
            flow_trigger=FlowTrigger.SCHEDULED_TASK
        )
        self._publish_flow_start(cache, FlowTrigger.SCHEDULED_TASK)
```

### 4.3 Worker Pattern: Graceful Degradation

```python
class MomentumSignal(OpportunityWorker):
    """Example: Worker that REQUIRES price."""
    
    def process(self) -> DispositionEnvelope:
        ctx = self._context_provider.get_base_context()
        
        # Fail fast if price required but unavailable
        if ctx.current_price is None:
            self._logger.warning(
                f"MomentumSignal skipped - no price data "
                f"(flow_trigger={ctx.flow_trigger})"
            )
            return DispositionEnvelope(
                disposition="STOP",
                reason="Price required but unavailable"
            )
        
        # Optionally: warn if price is stale
        if not ctx.has_realtime_price():
            self._logger.warning(
                f"Using derived/stale price for momentum "
                f"(flow_trigger={ctx.flow_trigger})"
            )
        
        # ... calculate momentum using ctx.current_price


class SentimentAnalyzer(ContextWorker):
    """Example: Worker that doesn't need price."""
    
    def process(self) -> DispositionEnvelope:
        ctx = self._context_provider.get_base_context()
        
        # Price not needed - works for all flow types
        news_events = self._news_provider.get_recent_news(
            end_time=ctx.timestamp
        )
        
        sentiment = self._analyze(news_events)
        self._context_provider.set_result_dto(
            self,
            SentimentDTO(sentiment=sentiment)
        )
        
        return DispositionEnvelope(disposition="CONTINUE")
```

---

## 5. Interface Updates

### 5.1 ITradingContextProvider.start_new_tick()

```python
def start_new_tick(
    self,
    tick_cache: TickCacheType,
    timestamp: datetime,
    current_price: Decimal | None,  # ✅ Now optional!
    asset: str,
    flow_trigger: FlowTrigger  # ✅ NEW parameter!
) -> None:
    """
    Configureert provider voor nieuwe flow.
    
    Args:
        tick_cache: Multi-asset cache
        timestamp: Flow trigger timestamp
        current_price: Market price (None if unavailable/market closed)
        asset: Asset identifier
        flow_trigger: What triggered this run (MARKET_TICK/NEWS_EVENT/SCHEDULED_TASK)
    """
    ...
```

---

## 6. Decision Summary

### ✅ RECOMMENDED APPROACH:

**BaseContextDTO with Optional Price + Flow Type:**
1. `current_price: Decimal | None` - Honest about availability
2. `flow_trigger: FlowTrigger` - Explicit about what initiated run
3. Helper methods (`has_realtime_price()`, `has_derived_price()`)
4. Workers implement graceful degradation (STOP if price required but None)

**Rationale:**
- ✅ Works for all flow types (market/news/schedule)
- ✅ Honest about data availability (price can be None)
- ✅ Enables flow-type-specific worker logic
- ✅ Minimal complexity (only 2 extra fields: flow_trigger + Optional price)
- ✅ Backwards compatible (workers can ignore flow_trigger if not needed)

**Trade-offs Accepted:**
- Workers moet None-check doen voor current_price
- Slightly violates "minimal" principe (maar noodzakelijk voor correctheid)

---

**Document Owner:** Architecture Team  
**Status:** ✅ Analysis Complete - Awaiting User Decision  
**Last Updated:** 2025-10-28
