# Event Architecture - Complete System Design

**Status:** Design  
**Versie:** 1.0  
**Laatst Bijgewerkt:** 2025-11-04

---

## Executive Summary

Dit document beschrijft de **complete event-driven architectuur** van SimpleTraderV3, van externe databronnen tot platform monitoring. Het definieert:

- **Event producenten en consumenten** (wie publish/subscribe)
- **Event scoping** (PLATFORM vs STRATEGY)
- **Event persistence** (EventStore voor durability)
- **Event buffering** (EventQueue voor async processing)
- **Delivery garanties** (at-least-once, ordering, idempotency)

**Kernprincipe:** Alle communicatie verloopt via het EventBus, met strikte scope isolatie en guaranteed delivery.

---

## Event Producenten & Consumenten - Complete Inventarisatie

### A. Externe Event Producenten (Platform Scope)

Alle externe bronnen publishen events met **`APL_*` prefix** (Application/Platform events) op `ScopeLevel.PLATFORM`.

#### A1. Market Data Providers

**OhlcvProvider** - OHLCV candle data
- Events: `APL_CANDLE_CLOSE_1M`, `APL_CANDLE_CLOSE_5M`, `APL_CANDLE_CLOSE_1H`, `APL_CANDLE_CLOSE_4H`, `APL_CANDLE_CLOSE_1D`
- Configuratie: Symbolen + timeframes via Platform Resources UI
- Implementatie: Wraps V2 DataLoader (backtest) / IAPIConnector (live)

**TickDataProvider** - Real-time tick data
- Events: `APL_TICK_BID`, `APL_TICK_ASK`, `APL_TICK_TRADE`
- Configuratie: Symbolen via Platform Resources UI
- Use case: High-frequency strategies

**OrderbookProvider** - Orderbook snapshots
- Events: `APL_ORDERBOOK_SNAPSHOT`, `APL_ORDERBOOK_UPDATE`
- Configuratie: Symbolen + depth levels
- Use case: Market microstructure analysis

#### A2. News & Sentiment Providers

**NewsProvider** - News feeds
- Events: `APL_NEWS_ARTICLE`, `APL_EARNINGS_REPORT`, `APL_REGULATORY_ANNOUNCEMENT`
- Configuratie: News sources + keywords via UI
- Use case: Sentiment-driven strategies

**SentimentAnalyzer** - Sentiment scoring
- Events: `APL_SENTIMENT_POSITIVE`, `APL_SENTIMENT_NEGATIVE`, `APL_SENTIMENT_NEUTRAL`
- Configuratie: Data sources + models
- Use case: AI-driven sentiment strategies

**SocialMediaProvider** - Social media feeds
- Events: `APL_TWITTER_MENTION`, `APL_REDDIT_DISCUSSION`
- Configuratie: Keywords + accounts
- Use case: Social sentiment strategies

#### A3. RSS & Web Feeds

**RssFeedConnector** - RSS feed monitoring
- Events: `APL_RSS_ITEM_NEW`, `APL_RSS_ITEM_UPDATED`
- Configuratie: RSS feed URLs
- Use case: Custom data sources

**WebScraperProvider** - Web scraping
- Events: `APL_WEBPAGE_CHANGED`, `APL_DATA_EXTRACTED`
- Configuratie: URLs + CSS selectors
- Use case: Alternative data sources

#### A4. Trading API Connectors

**ExchangeConnector** - Exchange API integration
- **Inbound Events** (van exchange naar platform):
  - `APL_ORDER_FILLED`
  - `APL_ORDER_CANCELLED`
  - `APL_ORDER_REJECTED`
  - `APL_POSITION_UPDATED`
  - `APL_BALANCE_CHANGED`
- **Outbound** (platform naar exchange):
  - Geen events - direct API calls via IOrderRouter interface
- Configuratie: API credentials + exchange selection
- Use case: Live trading execution

#### A5. Time-Based Triggers

**Scheduler** - Cron-based scheduling
- Events: `APL_DAILY_SCHEDULE`, `APL_HOURLY_SCHEDULE`, `APL_WEEKLY_SCHEDULE`, `APL_CUSTOM_CRON`
- Configuratie: Cron expressions via Platform Resources UI
- Use case: Periodic rebalancing, budget resets

**Eigenschappen:**
- **Event Adapter:** ✅ Alle componenten hebben EventAdapter
- **Scope:** `ScopeLevel.PLATFORM` (broadcast naar alle strategieën)
- **Critical:** `is_critical=False` (failures loggen, niet crashen)
- **Manifest Locatie:** `backend/platform/{component_name}/manifest.yaml`

---

### B. FlowInitiator (Event Vertaler)

**Rol:** Per-strategy platform component die externe events vertaalt naar strategy-internal events.

**Verantwoordelijkheden:**
1. **Subscribe** op `APL_*` events (platform scope)
2. **Initialize** strategy run via `StrategyCache.start_new_run()`
3. **Transform** event: verwijder `APL_` prefix
4. **Publish** internal event (strategy scope)

**Event Transformatie:**
```
Input (PLATFORM):        Output (STRATEGY):
APL_CANDLE_CLOSE_1H  →   CANDLE_CLOSE_1H
APL_NEWS_EVENT       →   NEWS_EVENT
APL_DAILY_SCHEDULE   →   DAILY_SCHEDULE
APL_ORDER_FILLED     →   ORDER_FILLED
```

**Scope Transitie:** `ScopeLevel.PLATFORM` → `ScopeLevel.STRATEGY`

**Configuratie (strategy_blueprint.yaml):**
```yaml
platform_components:
  flow_initiator:
    component_id: "platform/flow_initiator/v1.0.0"
    config:
      inputs:
        - event_name: APL_CANDLE_CLOSE_1H
          connector_id: candle_1h_trigger
        - event_name: APL_WEEKLY_SCHEDULE
          connector_id: weekly_trigger
      outputs:
        - connector_id: candle_1h_ready
          event_name: CANDLE_CLOSE_1H
        - connector_id: weekly_ready
          event_name: WEEKLY_SCHEDULE
```

**Eigenschappen:**
- **Event Adapter:** ✅ Per strategy instance
- **Scope:** PLATFORM (input) → STRATEGY (output)
- **Critical:** `is_critical=False`
- **Side Effect:** `StrategyCache.start_new_run()` (garantie voor workers)

**Zie ook:** [FlowInitiator Design](../development/backend/core/FLOW_INITIATOR_DESIGN.md)

---

### C. Strategie Componenten (Interne Communicatie)

**Rol:** Strategy workers die onderling communiceren binnen **strategy scope**.

**Workers en hun Events:**

**SignalDetector** - Signal/opportunity detection
- **Input:** `CANDLE_CLOSE_1H`, `NEWS_EVENT` (van FlowInitiator)
- **Output:** `SIGNAL_DETECTED`, `OPPORTUNITY_IDENTIFIED`

**RiskEvaluator** - Risk/threat assessment
- **Input:** `SIGNAL_DETECTED`, `OPPORTUNITY_IDENTIFIED`
- **Output:** `RISK_ASSESSED`, `THREAT_DETECTED`

**EntryPlanner** - Entry planning
- **Input:** `RISK_ASSESSED`
- **Output:** `ENTRY_PLAN_READY`

**PositionSizer** - Position sizing
- **Input:** `ENTRY_PLAN_READY`
- **Output:** `POSITION_SIZED`

**OrderRouter** - Order routing
- **Input:** `POSITION_SIZED`
- **Output:** `ORDER_PLACED`, `ORDER_ROUTING_FAILED`

**ExecutionMonitor** - Execution monitoring
- **Input:** `ORDER_FILLED`, `ORDER_CANCELLED` (van FlowInitiator)
- **Output:** `EXECUTION_COMPLETE`, `EXECUTION_FAILED`

**FlowTerminator** - Pipeline cleanup
- **Input:** `EXECUTION_COMPLETE`, `EXECUTION_FAILED`
- **Output:** Geen (side effect: `StrategyCache.clear_cache()`)

**Eigenschappen:**
- **Event Adapter:** ✅ Per worker instance
- **Scope:** `ScopeLevel.STRATEGY` met **verplichte** `strategy_instance_id`
- **Critical:** `is_critical=False` (strategy failures isoleren)
- **Isolatie:** Strategy A events nooit zichtbaar voor Strategy B

---

### D. Platform Componenten (Luisteren naar Strategieën)

**Rol:** Platform singletons die **alle strategieën monitoren** zonder te interfereren.

**PerformanceMonitor** - Performance tracking
- **Subscribe:** `EXECUTION_COMPLETE` (alle strategieën)
- **Actie:** Bereken P&L, Sharpe ratio, drawdown
- **Output:** Metrics naar dashboard

**AuditLogger** - Audit trail
- **Subscribe:** Alle strategy events (wildcard subscription)
- **Actie:** Persist naar audit database
- **Output:** Audit logs voor compliance

**AlertManager** - Alert generation
- **Subscribe:** `THREAT_DETECTED`, `EXECUTION_FAILED`
- **Actie:** Generate alerts naar users
- **Output:** Email/SMS/Telegram notificaties

**RiskAggregator** - Portfolio-level risk
- **Subscribe:** `POSITION_SIZED`, `RISK_ASSESSED` (alle strategieën)
- **Actie:** Aggregate risk across strategies
- **Output:** Portfolio risk metrics

**Eigenschappen:**
- **Event Adapter:** ✅ Singleton per platform component
- **Scope Filter:** `SubscriptionScope(level=STRATEGY, strategy_instance_id=None)` (alle strategieën)
- **Critical:** `is_critical=False` (monitoring failures niet fataal)
- **Read-Only:** Alleen observeren, geen strategy state wijzigen

---

### E. Platform ↔ Strategie Communicatie (Bidirectioneel)

**Rol:** Platform diensten die **interactie hebben** met strategieën (niet alleen observeren).

#### Platform → Strategie

**ResourceManager** - Resource limits
- **Publish:** `APL_RESOURCE_LIMIT_REACHED` (platform scope)
- **Actie:** Strategy FlowInitiator ontvangt → pauzeert strategy
- **Use Case:** RAM/CPU limits, rate limiting

**MaintenanceScheduler** - Planned downtime
- **Publish:** `APL_MAINTENANCE_STARTING` (platform scope)
- **Actie:** Strategies ontvangen → graceful shutdown
- **Use Case:** System upgrades, database backups

#### Strategie → Platform

**OrderRouter** (worker) - Order execution
- **Publish:** `ORDER_PLACED` (strategy scope)
- **Subscribe:** ExchangeConnector luistert (strategy-specific)
- **Actie:** ExchangeConnector plaatst order via API
- **Use Case:** Live trading execution

**PositionManager** (worker) - Position tracking
- **Publish:** `POSITION_CLOSED` (strategy scope)
- **Subscribe:** AccountingService luistert
- **Actie:** Update portfolio accounting
- **Use Case:** Portfolio management

**Eigenschappen:**
- **Scope:** Mixed (PLATFORM of STRATEGY afhankelijk van richting)
- **Critical:** `is_critical=False`
- **Two-Way:** Zowel publish als subscribe

---

### F. Platform Componenten Onderling

**Rol:** Platform singletons die **onderling coördineren** voor system-level operaties.

**ConfigManager** - Configuration management
- **Publish:** `CONFIG_UPDATED` (platform scope)
- **Subscribe:** ComponentRegistry, WorkerFactory
- **Actie:** Reload manifests, rebuild components
- **Use Case:** Hot-reload configuratie

**HealthMonitor** - Component health
- **Publish:** `COMPONENT_FAILED` (platform scope)
- **Subscribe:** AutoRecovery
- **Actie:** Start recovery procedures
- **Use Case:** Self-healing architecture

**ResourceAllocator** - Resource allocation
- **Publish:** `RESOURCE_FREED` (platform scope)
- **Subscribe:** SchedulerService
- **Actie:** Schedule queued strategies
- **Use Case:** Resource optimization

**Eigenschappen:**
- **Event Adapter:** ✅ Singleton per component
- **Scope:** `ScopeLevel.PLATFORM` (singleton communicatie)
- **Critical:** `is_critical=True` ⚠️ (failures crashen systeem)
- **System-Level:** Infrastructure events, niet strategy-gerelateerd

---

## Event Persistence & Buffering Architectuur

### Het "Gemiste Events" Probleem

**Scenario 1: Strategy Offline**
```
Platform publiceert: APL_CANDLE_CLOSE_1H (10:00)
Strategy A: Offline voor maintenance
→ Event gemist zonder EventStore ❌
```

**Scenario 2: System Crash**
```
Platform publiceert: APL_ORDER_FILLED (critical event)
System crasht voordat handler uitgevoerd
→ Event gemist, trade state inconsistent ❌
```

**Scenario 3: Backpressure**
```
Platform publiceert: 1000 APL_TICK events/sec
Strategy processing: 100 events/sec
→ Events gedropped, data loss ❌
```

---

### Oplossing: Event Store + Queue Laag

#### Architectuur Lagen

```
┌─────────────────────────────────────────────────────────┐
│ A. Externe Bronnen (Platform Scope)                     │
│ - Market APIs, News Feeds, Scheduler                    │
│ - Publish: APL_* events                                 │
└────────────────┬────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────┐
│ EventStore (Persistence Layer)                          │
│ - Persist ALL platform events                           │
│ - Replay capability voor recovery                       │
│ - Event versioning voor schema evolution                │
└────────────────┬────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────┐
│ EventBus (Routing Layer)                                │
│ - Scope filtering: PLATFORM vs STRATEGY                 │
│ - Thread-safe N-to-N communication                      │
│ - Synchronous dispatch (current)                        │
└─────────┬───────────────────────────────────────────────┘
          ↓
┌─────────────────────────────────────────────────────────┐
│ B. FlowInitiator (Per-Strategy Translator)              │
│ - Transform: APL_* → internal events                    │
│ - Initialize: StrategyCache.start_new_run()            │
│ - Scope: PLATFORM → STRATEGY                            │
└────────────────┬────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────┐
│ EventQueue (Per-Strategy Buffering)                     │
│ - Async processing queue                                │
│ - Backpressure handling                                 │
│ - At-least-once delivery                                │
│ - FIFO ordering per strategy                            │
└────────────────┬────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────┐
│ C. Strategy Workers (Internal Events)                   │
│ - Process events from queue                             │
│ - Publish results to EventBus (strategy scope)          │
│ - Idempotent processing (duplicate detection)           │
└────────────────┬────────────────────────────────────────┘
                 ↓
          ┌──────┴──────┐
          ↓             ↓
┌──────────────┐ ┌──────────────────┐
│ D. Platform  │ │ E. Platform ↔    │
│    Monitors  │ │    Strategy      │
│ (Subscribe)  │ │    Bi-direct     │
└──────────────┘ └──────────────────┘
          ↓             ↓
┌─────────────────────────────────────┐
│ F. Platform Onderling (CRITICAL)    │
│ - ConfigManager, HealthMonitor      │
└─────────────────────────────────────┘
```

---

### EventStore Design

**Verantwoordelijkheid:** Persistent storage voor alle platform events.

**Schema:**
```python
@dataclass
class EventRecord:
    event_id: str              # UUID
    event_name: str            # APL_CANDLE_CLOSE_1H
    timestamp: datetime        # Event tijdstip
    scope: ScopeLevel          # PLATFORM of STRATEGY
    strategy_instance_id: str | None  # Voor STRATEGY scope
    payload: dict              # Serialized Pydantic DTO
    payload_schema_version: int       # Voor backward compatibility
    created_at: datetime       # Storage tijdstip
    processed: bool            # Delivery tracking
    processed_at: datetime | None
    retry_count: int           # Failed delivery tracking
    dead_letter: bool          # DLQ flag
```

**Storage Backend:**
- **Development:** SQLite (`events.db`)
- **Production:** PostgreSQL met partitioning (per dag/week)

**Operations:**
```python
class IEventStore:
    def persist(self, event: BaseModel, scope: ScopeLevel, 
                strategy_instance_id: str | None) -> str:
        """Persist event, return event_id."""
    
    def get_unprocessed_events(self, strategy_instance_id: str) -> List[EventRecord]:
        """Query unprocessed events voor strategy recovery."""
    
    def mark_processed(self, event_id: str) -> None:
        """Mark event als processed na successful delivery."""
    
    def replay_events(self, strategy_instance_id: str, 
                     from_timestamp: datetime, 
                     to_timestamp: datetime) -> Iterator[EventRecord]:
        """Replay events voor backtest of recovery."""
    
    def move_to_dead_letter(self, event_id: str, reason: str) -> None:
        """Move failed event naar Dead Letter Queue."""
```

**Retention Policy:**
- **Platform Events:** 30 dagen (configurable)
- **Strategy Events:** 7 dagen (configurable)
- **Dead Letter Queue:** 90 dagen (compliance)

---

### EventQueue Design

**Verantwoordelijkheid:** Per-strategy async buffering met backpressure handling.

**Queue Structuur:**
```python
# Per-strategy queues
strategy_queues: Dict[str, asyncio.Queue[EventRecord]] = {
    "STR_ABC_INSTANCE_001": asyncio.Queue(maxsize=1000),
    "STR_XYZ_INSTANCE_002": asyncio.Queue(maxsize=1000)
}

# Dead Letter Queue (shared)
dead_letter_queue: asyncio.Queue[EventRecord] = asyncio.Queue()
```

**Queue Configuratie (per strategy):**
```yaml
# strategy_blueprint.yaml
runtime:
  event_queue:
    maxsize: 1000          # Max events in queue
    timeout_sec: 30        # Dequeue timeout
    max_retries: 3         # Failed delivery retries
    backpressure_policy: "drop_oldest"  # of "block" of "drop_newest"
```

**Backpressure Policies:**
- **`drop_oldest`:** Remove oudste event bij vol queue (default)
- **`block`:** Block producer tot queue ruimte heeft (risico: deadlock)
- **`drop_newest`:** Ignore nieuwe events bij vol queue

**Operations:**
```python
class EventQueueManager:
    def enqueue(self, strategy_instance_id: str, event: EventRecord) -> bool:
        """Enqueue event, return success."""
    
    async def dequeue(self, strategy_instance_id: str) -> EventRecord:
        """Dequeue next event (async, waits if empty)."""
    
    def get_queue_depth(self, strategy_instance_id: str) -> int:
        """Query current queue size."""
    
    def flush_queue(self, strategy_instance_id: str) -> None:
        """Clear queue (voor strategy stop)."""
```

---

### Delivery Garanties

**At-Least-Once Delivery:**
1. Event persist in EventStore (`processed=False`)
2. Event enqueue in EventQueue
3. Worker processes event
4. Worker commit result
5. EventStore mark processed (`processed=True`)

**Bij failure tussen stap 3-5:** Event blijft `processed=False` → retry bij recovery.

**Idempotency Requirement:**
Workers moeten **idempotent** zijn (duplicate events negeren):
```python
class SignalDetector(StandardWorker):
    def on_market_trigger(self, event: CandleCloseEvent) -> DispositionEnvelope:
        # Check duplicate
        event_id = event.metadata.event_id
        if self._cache.is_event_processed(event_id):
            return DispositionEnvelope(disposition=Disposition.CONTINUE)
        
        # Process event
        result = self._detect_signal(event)
        
        # Mark processed
        self._cache.mark_event_processed(event_id)
        
        return result
```

**FIFO Ordering:**
Events voor **dezelfde strategy** worden altijd in volgorde geprocessed:
```
Queue STR_ABC:
  1. APL_CANDLE_CLOSE_1H (10:00)
  2. APL_CANDLE_CLOSE_1H (11:00)  ← Blocked tot 1 processed
  3. APL_CANDLE_CLOSE_1H (12:00)  ← Blocked tot 2 processed
```

**No Ordering Guarantee Cross-Strategy:**
Strategy A en Strategy B kunnen events in verschillende volgorde processen.

---

### Recovery Mechanisme

**Strategy Restart Flow:**
```python
# backend/assembly/bootstrap.py

class StrategyBootstrap:
    def recover_strategy(self, strategy_instance_id: str) -> None:
        """Recover strategy from EventStore."""
        
        # 1. Query unprocessed events
        event_store = self._get_event_store()
        unprocessed = event_store.get_unprocessed_events(strategy_instance_id)
        
        logger.info(f"Recovering {len(unprocessed)} events for {strategy_instance_id}")
        
        # 2. Re-enqueue events
        queue_manager = self._get_queue_manager()
        for event_record in unprocessed:
            queue_manager.enqueue(strategy_instance_id, event_record)
        
        # 3. Resume processing
        self._start_strategy_worker_pool(strategy_instance_id)
```

**Replay for Backtest:**
```python
# services/backtest_service.py

class BacktestService:
    def run_backtest(
        self, 
        strategy_id: str, 
        from_date: datetime, 
        to_date: datetime
    ) -> BacktestResult:
        """Run backtest by replaying stored events."""
        
        # Create backtest strategy instance
        instance_id = self._create_backtest_instance(strategy_id)
        
        # Replay events from EventStore
        event_store = self._get_event_store()
        events = event_store.replay_events(
            strategy_instance_id=None,  # Platform events
            from_timestamp=from_date,
            to_timestamp=to_date
        )
        
        # Inject events into strategy
        for event_record in events:
            self._event_bus.publish(
                event_name=event_record.event_name,
                payload=self._deserialize(event_record.payload),
                scope=ScopeLevel.PLATFORM
            )
        
        # Collect results
        return self._collect_backtest_results(instance_id)
```

---

### Dead Letter Queue (DLQ)

**Rol:** Storage voor events die **niet geprocessed kunnen worden** na max retries.

**DLQ Flow:**
```python
class EventQueueWorker:
    async def process_event(self, event_record: EventRecord) -> None:
        """Process event with retry logic."""
        
        for attempt in range(self._max_retries):
            try:
                # Invoke worker handler
                result = await self._invoke_worker(event_record)
                
                # Mark processed
                self._event_store.mark_processed(event_record.event_id)
                return
                
            except Exception as e:
                logger.warning(f"Retry {attempt+1}/{self._max_retries}: {e}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        # Max retries exceeded → DLQ
        logger.error(f"Event {event_record.event_id} moved to DLQ")
        self._event_store.move_to_dead_letter(
            event_id=event_record.event_id,
            reason=f"Max retries exceeded: {str(e)}"
        )
```

**DLQ UI:**
Strategy Builder UI toont DLQ events voor manual retry of investigation:
```
Dead Letter Queue - Strategy: smart_dca_v1
┌────────────────────────────────────────────────────────┐
│ Event ID         Event Name          Failed At  Reason │
├────────────────────────────────────────────────────────┤
│ EVT_ABC123       CANDLE_CLOSE_1H    10:05      Worker  │
│                                                 timeout │
│ EVT_XYZ789       ORDER_FILLED       11:23      Invalid │
│                                                 payload │
└────────────────────────────────────────────────────────┘
[Retry Selected] [Delete] [View Details]
```

---

## Event Adapter Mapping - Complete Overzicht

| Component | Type | Event Adapter | Scope | Critical | Manifest Locatie |
|-----------|------|---------------|-------|----------|------------------|
| **A. Externe Bronnen** |
| OhlcvProvider | Platform | ✅ | PLATFORM | ❌ | `backend/platform/ohlcv_provider/` |
| TickDataProvider | Platform | ✅ | PLATFORM | ❌ | `backend/platform/tick_provider/` |
| OrderbookProvider | Platform | ✅ | PLATFORM | ❌ | `backend/platform/orderbook_provider/` |
| NewsProvider | Platform | ✅ | PLATFORM | ❌ | `backend/platform/news_provider/` |
| SentimentAnalyzer | Platform | ✅ | PLATFORM | ❌ | `backend/platform/sentiment_analyzer/` |
| SocialMediaProvider | Platform | ✅ | PLATFORM | ❌ | `backend/platform/social_provider/` |
| RssFeedConnector | Platform | ✅ | PLATFORM | ❌ | `backend/platform/rss_connector/` |
| WebScraperProvider | Platform | ✅ | PLATFORM | ❌ | `backend/platform/web_scraper/` |
| ExchangeConnector | Platform | ✅ | PLATFORM | ❌ | `backend/platform/exchange_connector/` |
| Scheduler | Platform | ✅ | PLATFORM | ❌ | `backend/platform/scheduler/` |
| **B. Event Vertaler** |
| FlowInitiator | Platform | ✅ | PLATFORM → STRATEGY | ❌ | `backend/config/manifests/` |
| **C. Strategy Workers** |
| SignalDetector | Worker | ✅ | STRATEGY | ❌ | `plugins/workers/signal_generators/` |
| RiskEvaluator | Worker | ✅ | STRATEGY | ❌ | `plugins/workers/regime_filters/` |
| EntryPlanner | Worker | ✅ | STRATEGY | ❌ | `plugins/workers/entry_planners/` |
| PositionSizer | Worker | ✅ | STRATEGY | ❌ | `plugins/workers/position_sizers/` |
| OrderRouter | Worker | ✅ | STRATEGY | ❌ | `plugins/workers/order_routers/` |
| ExecutionMonitor | Worker | ✅ | STRATEGY | ❌ | `plugins/workers/execution_monitors/` |
| FlowTerminator | Platform | ✅ | STRATEGY | ❌ | `backend/config/manifests/` |
| **D. Platform Monitors** |
| PerformanceMonitor | Platform | ✅ | STRATEGY (listen all) | ❌ | `backend/platform/performance_monitor/` |
| AuditLogger | Platform | ✅ | STRATEGY (listen all) | ❌ | `backend/platform/audit_logger/` |
| AlertManager | Platform | ✅ | STRATEGY (listen all) | ❌ | `backend/platform/alert_manager/` |
| RiskAggregator | Platform | ✅ | STRATEGY (listen all) | ❌ | `backend/platform/risk_aggregator/` |
| **E. Platform ↔ Strategy** |
| ResourceManager | Platform | ✅ | PLATFORM | ❌ | `backend/platform/resource_manager/` |
| MaintenanceScheduler | Platform | ✅ | PLATFORM | ❌ | `backend/platform/maintenance_scheduler/` |
| AccountingService | Platform | ✅ | STRATEGY (listen all) | ❌ | `backend/platform/accounting_service/` |
| **F. Platform Onderling** |
| ConfigManager | Platform | ✅ | PLATFORM | ✅ | `backend/platform/config_manager/` |
| HealthMonitor | Platform | ✅ | PLATFORM | ✅ | `backend/platform/health_monitor/` |
| ResourceAllocator | Platform | ✅ | PLATFORM | ✅ | `backend/platform/resource_allocator/` |

**Legend:**
- **Event Adapter:** Component heeft EventAdapter voor EventBus integratie
- **Scope:** `PLATFORM` (broadcast) of `STRATEGY` (isolated)
- **Critical:** `is_critical=True` crasht systeem bij failure
- **Manifest Locatie:** Waar manifest.yaml zich bevindt

---

## Event Scoping - Isolatie & Filtering

### ScopeLevel Enum

```python
# backend/core/interfaces/eventbus.py

class ScopeLevel(str, Enum):
    """Event scope levels voor isolatie."""
    PLATFORM = "PLATFORM"   # Broadcast naar alle strategieën
    STRATEGY = "STRATEGY"   # Isolated binnen strategy instance
```

### SubscriptionScope Rules

**Platform Scope Subscribe (broadcast ontvangers):**
```python
# Platform component subscribes op platform events
scope = SubscriptionScope(
    level=ScopeLevel.PLATFORM,
    strategy_instance_id=None  # Not applicable
)
# Ontvangt: Alle PLATFORM scope publishes
```

**Strategy Scope Subscribe (isolated ontvanger):**
```python
# Worker subscribes binnen eigen strategy
scope = SubscriptionScope(
    level=ScopeLevel.STRATEGY,
    strategy_instance_id="STR_ABC_INSTANCE_001"
)
# Ontvangt: Alleen events met matching strategy_instance_id
```

**Cross-Strategy Monitor (alle strategieën observeren):**
```python
# Platform monitor subscribes op alle strategies
scope = SubscriptionScope(
    level=ScopeLevel.STRATEGY,
    strategy_instance_id=None  # Wildcard: alle strategieën
)
# Ontvangt: Alle STRATEGY scope publishes (any strategy_instance_id)
```

### Publish Requirements

**Platform Publish:**
```python
event_bus.publish(
    event_name="APL_CANDLE_CLOSE_1H",
    payload=CandleCloseEvent(...),
    scope=ScopeLevel.PLATFORM,
    strategy_instance_id=None  # Not applicable
)
```

**Strategy Publish:**
```python
event_bus.publish(
    event_name="SIGNAL_DETECTED",
    payload=SignalEvent(...),
    scope=ScopeLevel.STRATEGY,
    strategy_instance_id="STR_ABC_INSTANCE_001"  # REQUIRED
)
```

**Validation:**
```python
if scope == ScopeLevel.STRATEGY and strategy_instance_id is None:
    raise ValueError("strategy_instance_id required for STRATEGY scope")
```

---

## Event Naming Conventions

### Platform Events (Externe Bronnen)

**Pattern:** `APL_{SOURCE}_{EVENT_TYPE}` (Application/Platform prefix)

**Voorbeelden:**
- Market Data: `APL_CANDLE_CLOSE_1H`, `APL_TICK_BID`, `APL_ORDERBOOK_SNAPSHOT`
- News: `APL_NEWS_ARTICLE`, `APL_EARNINGS_REPORT`
- Time: `APL_DAILY_SCHEDULE`, `APL_HOURLY_SCHEDULE`
- Exchange: `APL_ORDER_FILLED`, `APL_POSITION_UPDATED`

### Strategy-Internal Events

**Pattern:** `{EVENT_TYPE}` (geen prefix, geen suffix)

**FlowInitiator Transformatie:**
```
APL_CANDLE_CLOSE_1H  →  CANDLE_CLOSE_1H
APL_NEWS_EVENT       →  NEWS_EVENT
APL_ORDER_FILLED     →  ORDER_FILLED
```

**Worker Events:**
- Signals: `SIGNAL_DETECTED`, `OPPORTUNITY_IDENTIFIED`
- Risk: `RISK_ASSESSED`, `THREAT_DETECTED`
- Planning: `ENTRY_PLAN_READY`, `POSITION_SIZED`
- Execution: `ORDER_PLACED`, `EXECUTION_COMPLETE`

### Platform Management Events

**Pattern:** `{COMPONENT}_{ACTION}` (geen APL_ prefix)

**Voorbeelden:**
- Config: `CONFIG_UPDATED`, `CONFIG_RELOAD_REQUESTED`
- Health: `COMPONENT_FAILED`, `COMPONENT_RECOVERED`
- Resources: `RESOURCE_FREED`, `RESOURCE_LIMIT_REACHED`

---

## Event Versioning & Schema Evolution

### Event DTO Versioning

**Problem:** Event schema changes breken oude strategy instances.

**Solution:** Semantic versioning in event DTOs:

```python
# backend/dtos/shared/events/candle_close_event.py

class CandleCloseEventV1(BaseModel):
    """Version 1: Initial schema."""
    timestamp: datetime
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    
    class Config:
        schema_version = 1

class CandleCloseEventV2(BaseModel):
    """Version 2: Added VWAP field."""
    timestamp: datetime
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    vwap: float  # NEW FIELD
    
    class Config:
        schema_version = 2

# Type alias points to latest version
CandleCloseEvent = CandleCloseEventV2
```

**EventStore Schema Tracking:**
```python
@dataclass
class EventRecord:
    payload_schema_version: int  # Track DTO version
    payload: dict                 # Serialized DTO
```

**Deserialization met Versioning:**
```python
class EventDeserializer:
    def deserialize(self, event_record: EventRecord) -> BaseModel:
        """Deserialize met backward compatibility."""
        
        schema_version = event_record.payload_schema_version
        event_name = event_record.event_name
        
        # Lookup DTO class
        dto_class = self._get_dto_class(event_name, schema_version)
        
        # Deserialize
        return dto_class(**event_record.payload)
    
    def _get_dto_class(self, event_name: str, version: int) -> Type[BaseModel]:
        """Lookup DTO class by name and version."""
        registry = {
            ("CANDLE_CLOSE", 1): CandleCloseEventV1,
            ("CANDLE_CLOSE", 2): CandleCloseEventV2,
        }
        return registry.get((event_name, version), CandleCloseEvent)
```

### Migration Strategy

**Forward Compatibility (oude workers → nieuwe events):**
```python
class CandleCloseEventV2(BaseModel):
    vwap: float = 0.0  # Default value voor oude workers
```

**Backward Compatibility (nieuwe workers → oude events):**
```python
class SignalDetector:
    def on_market_trigger(self, event: CandleCloseEvent) -> DispositionEnvelope:
        # Handle both V1 and V2
        vwap = getattr(event, 'vwap', None)
        if vwap is None:
            vwap = self._calculate_vwap(event)  # Fallback
```

---

## Testing Strategy

### Unit Tests

**EventStore Tests:**
```python
# tests/unit/core/test_event_store.py

class TestEventStore:
    def test_persist_and_query_unprocessed(self):
        """Test event persistence and recovery query."""
        store = EventStore(db_path=":memory:")
        
        # Persist event
        event_id = store.persist(
            event=CandleCloseEvent(...),
            scope=ScopeLevel.PLATFORM,
            strategy_instance_id=None
        )
        
        # Query unprocessed
        unprocessed = store.get_unprocessed_events("STR_ABC")
        assert len(unprocessed) == 1
        assert unprocessed[0].event_id == event_id
        
        # Mark processed
        store.mark_processed(event_id)
        
        # Verify empty
        assert len(store.get_unprocessed_events("STR_ABC")) == 0
```

**EventQueue Tests:**
```python
# tests/unit/core/test_event_queue.py

class TestEventQueue:
    async def test_backpressure_drop_oldest(self):
        """Test backpressure policy: drop_oldest."""
        queue_mgr = EventQueueManager(
            maxsize=2,
            backpressure_policy="drop_oldest"
        )
        
        # Fill queue
        queue_mgr.enqueue("STR_ABC", event1)
        queue_mgr.enqueue("STR_ABC", event2)
        
        # Enqueue 3rd event (triggers backpressure)
        queue_mgr.enqueue("STR_ABC", event3)
        
        # Verify event1 dropped, event2 and event3 remain
        assert await queue_mgr.dequeue("STR_ABC") == event2
        assert await queue_mgr.dequeue("STR_ABC") == event3
```

### Integration Tests

**End-to-End Event Flow:**
```python
# tests/integration/test_event_flow_e2e.py

class TestEventFlowE2E:
    async def test_platform_event_to_worker_with_persistence(self):
        """Test complete flow: Platform → EventStore → FlowInitiator → Worker."""
        
        # Setup
        event_store = EventStore(db_path=":memory:")
        event_bus = EventBus()
        queue_mgr = EventQueueManager()
        
        # Bootstrap FlowInitiator
        flow_initiator = self._bootstrap_flow_initiator(
            strategy_id="STR_ABC",
            event_store=event_store,
            queue_mgr=queue_mgr
        )
        
        # Bootstrap Worker
        worker = SignalDetector("detector_1")
        
        # Publish platform event
        event_bus.publish(
            event_name="APL_CANDLE_CLOSE_1H",
            payload=CandleCloseEvent(...),
            scope=ScopeLevel.PLATFORM
        )
        
        # Verify persistence
        unprocessed = event_store.get_unprocessed_events("STR_ABC")
        assert len(unprocessed) == 1
        
        # Process from queue
        event_record = await queue_mgr.dequeue("STR_ABC")
        result = worker.on_market_trigger(event_record.payload)
        
        # Mark processed
        event_store.mark_processed(event_record.event_id)
        
        # Verify processed
        assert len(event_store.get_unprocessed_events("STR_ABC")) == 0
```

---

## Implementation Components

### Core Components (Backend Layer)

**Event Infrastructure:**
- `backend/core/eventbus.py` - EventBus implementation (exists)
- `backend/core/event_store.py` - EventStore implementation (NEW)
- `backend/core/event_queue.py` - EventQueue implementation (NEW)
- `backend/core/event_deserializer.py` - Versioned deserialization (NEW)

**Platform Event Sources:**
- `backend/platform/ohlcv_provider/` - OHLCV data provider (NEW)
- `backend/platform/scheduler/` - Time-based triggers (NEW)
- `backend/platform/news_provider/` - News feed provider (NEW)
- `backend/platform/exchange_connector/` - Exchange API (NEW)

**Platform Monitors:**
- `backend/platform/performance_monitor/` - P&L tracking (NEW)
- `backend/platform/audit_logger/` - Audit trail (NEW)
- `backend/platform/alert_manager/` - Alert generation (NEW)

**Platform Management:**
- `backend/platform/config_manager/` - Config management (NEW)
- `backend/platform/health_monitor/` - Health monitoring (NEW)
- `backend/platform/resource_allocator/` - Resource management (NEW)

### Service Components (Service Layer)

**Platform Resource Services:**
- `services/api_services/ohlcv_provider_config_service.py` - OHLCV config (NEW)
- `services/api_services/scheduler_config_service.py` - Scheduler config (NEW)
- `services/api_services/news_provider_config_service.py` - News config (NEW)

**Event Management Services:**
- `services/event_store_service.py` - EventStore queries (NEW)
- `services/event_replay_service.py` - Replay functionality (NEW)
- `services/dead_letter_queue_service.py` - DLQ management (NEW)

### Frontend API (Frontend Layer)

**Platform Resources Endpoints:**
- `frontends/web/api/platform_resources/ohlcv_endpoints.py` - OHLCV CRUD (NEW)
- `frontends/web/api/platform_resources/scheduler_endpoints.py` - Scheduler CRUD (NEW)
- `frontends/web/api/platform_resources/news_endpoints.py` - News CRUD (NEW)

**Event Management Endpoints:**
- `frontends/web/api/event_management/event_store_endpoints.py` - EventStore queries (NEW)
- `frontends/web/api/event_management/dlq_endpoints.py` - DLQ UI (NEW)

### UI Integration (Frontend Layer)

**Strategy Builder UI:**
- Platform Resources tab (CRUD voor event sources)
- Event source selection in FlowInitiator config
- Real-time event preview

**Operations Dashboard:**
- Dead Letter Queue UI
- Event replay interface
- Event statistics & monitoring

---

## Related Documentation

- **FlowInitiator Design:** [FlowInitiator](../development/backend/core/FLOW_INITIATOR_DESIGN.md)
- **FlowInitiator Manifest:** [FlowInitiator Manifest](../development/backend/core/FLOW_INITIATOR_MANIFEST.md)
- **Platform Components:** [Platform Components](PLATFORM_COMPONENTS.md)
- **Event-Driven Wiring:** [Event-Driven Wiring](EVENT_DRIVEN_WIRING.md)
- **StrategyCache:** [StrategyCache Reference](../reference/platform/strategy_cache.md)

---

## Design Principles

### 1. Event Isolation via Scoping

**Platform Scope:** Broadcast events naar alle strategieën
- Use case: Market data, tijd triggers, nieuws
- Geen strategy_instance_id vereist
- FlowInitiator filtert relevante events

**Strategy Scope:** Isolated events binnen strategy instance
- Use case: Worker-to-worker communicatie
- strategy_instance_id VERPLICHT
- Andere strategieën zien deze events NIET

### 2. Guaranteed Delivery via EventStore

**At-Least-Once:** Events worden ALTIJD gepersisteerd voor processing
- EventStore.persist() VOOR EventBus.publish()
- Retry mechanisme bij failures
- Recovery query bij strategy restart

**Idempotency:** Workers moeten duplicates kunnen detecteren
- StrategyCache.is_event_processed(event_id)
- Metadata in event DTOs (event_id, timestamp)

### 3. Backpressure Handling via EventQueue

**Async Processing:** Queues decoupling producers van consumers
- Producers: Platform event sources (high throughput)
- Consumers: Strategy workers (variable throughput)
- Queue maxsize voorkomt memory overflow

**Configurable Policies:** Strategy-specific backpressure handling
- `drop_oldest`: Real-time strategies (latest data most relevant)
- `drop_newest`: Historical strategies (complete dataset vereist)
- `block`: Critical events (kan deadlock veroorzaken)

### 4. Schema Evolution via Versioning

**Backward Compatibility:** Oude workers kunnen nieuwe events processen
- Default values voor nieuwe velden
- Optional fields in nieuwe schema versions

**Forward Compatibility:** Nieuwe workers kunnen oude events processen
- Fallback logic voor missende velden
- Schema version tracking in EventStore

### 5. Observability via Platform Monitors

**Read-Only Monitoring:** Platform components observeren zonder interferentie
- PerformanceMonitor, AuditLogger, AlertManager
- Subscribe met `strategy_instance_id=None` (alle strategieën)
- is_critical=False (failures niet fataal)

### 6. Critical Infrastructure Protection

**Platform Singleton Failures:** System-level crashes bij critical component failure
- ConfigManager, HealthMonitor, ResourceAllocator
- is_critical=True (raises CriticalEventHandlerError)
- Rational: Infrastructure failure = stop alles, niet half-broken state

---

## Open Issues & Future Work

### Phase 1 (MVP)
- [ ] EventStore implementation (SQLite backend)
- [ ] EventQueue implementation (asyncio.Queue)
- [ ] EventStore UI (replay, DLQ management)
- [ ] Basic recovery mechanisme

### Phase 2 (Production)
- [ ] PostgreSQL backend voor EventStore
- [ ] Event partitioning (performance)
- [ ] Distributed EventQueue (Redis/RabbitMQ)
- [ ] Advanced replay (time-travel debugging)

### Phase 3 (Enterprise)
- [ ] Event versioning migrations (auto-upgrade)
- [ ] Cross-strategy event correlation (causality tracking)
- [ ] Event analytics dashboard
- [ ] Event-driven alerting (complex event processing)

---

**Document Einde**
