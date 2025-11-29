# Event Architecture - Conceptual Model

**Status:** Design  
**Version:** 2.0  
**Last Updated:** 2025-11-29

---

## 1. Executive Summary

This document describes the **conceptual event-driven architecture** of the platform, from external data sources to platform monitoring. It defines:

- **Event producers and consumers** (who publishes/subscribes)
- **Event scoping** (PLATFORM vs STRATEGY)
- **Event naming conventions**
- **Design principles**

**Core Principle:** All communication flows through the EventBus, with strict scope isolation.

**Related:** See [EVENT_PERSISTENCE.md](EVENT_PERSISTENCE.md) for durability, EventStore, EventQueue, and delivery guarantees.

---

## 2. Event Producers & Consumers - Complete Inventory

### 2.1 External Event Producers (Platform Scope)

All external sources publish events with **`APL_*` prefix** (Application/Platform events) on `ScopeLevel.PLATFORM`.

#### Market Data Providers

| Provider | Events | Configuration |
|----------|--------|---------------|
| **OhlcvProvider** | `APL_CANDLE_CLOSE_1M`, `APL_CANDLE_CLOSE_5M`, `APL_CANDLE_CLOSE_1H`, `APL_CANDLE_CLOSE_4H`, `APL_CANDLE_CLOSE_1D` | Symbols + timeframes via Platform Resources UI |
| **TickDataProvider** | `APL_TICK_BID`, `APL_TICK_ASK`, `APL_TICK_TRADE` | Symbols via Platform Resources UI |
| **OrderbookProvider** | `APL_ORDERBOOK_SNAPSHOT`, `APL_ORDERBOOK_UPDATE` | Symbols + depth levels |

#### News & Sentiment Providers

| Provider | Events | Use Case |
|----------|--------|----------|
| **NewsProvider** | `APL_NEWS_ARTICLE`, `APL_EARNINGS_REPORT`, `APL_REGULATORY_ANNOUNCEMENT` | Sentiment-driven strategies |
| **SentimentAnalyzer** | `APL_SENTIMENT_POSITIVE`, `APL_SENTIMENT_NEGATIVE`, `APL_SENTIMENT_NEUTRAL` | AI-driven sentiment strategies |
| **SocialMediaProvider** | `APL_TWITTER_MENTION`, `APL_REDDIT_DISCUSSION` | Social sentiment strategies |

#### RSS & Web Feeds

| Provider | Events | Use Case |
|----------|--------|----------|
| **RssFeedConnector** | `APL_RSS_ITEM_NEW`, `APL_RSS_ITEM_UPDATED` | Custom data sources |
| **WebScraperProvider** | `APL_WEBPAGE_CHANGED`, `APL_DATA_EXTRACTED` | Alternative data sources |

#### Trading API Connectors

**ExchangeConnector** - Exchange API integration:
- **Inbound Events** (from exchange to platform):
  - `APL_ORDER_FILLED`
  - `APL_ORDER_CANCELLED`
  - `APL_ORDER_REJECTED`
  - `APL_POSITION_UPDATED`
  - `APL_BALANCE_CHANGED`
- **Outbound** (platform to exchange):
  - No events - direct API calls via IOrderRouter interface

#### Time-Based Triggers

**Scheduler** - Cron-based scheduling:
- Events: `APL_DAILY_SCHEDULE`, `APL_HOURLY_SCHEDULE`, `APL_WEEKLY_SCHEDULE`, `APL_CUSTOM_CRON`
- Use case: Periodic rebalancing, budget resets

**Properties (all external producers):**
- **Event Adapter:** ✅ All components have EventAdapter
- **Scope:** `ScopeLevel.PLATFORM` (broadcast to all strategies)
- **Critical:** `is_critical=False` (failures log, don't crash)

---

### 2.2 FlowInitiator (Event Translator)

**Role:** Per-strategy platform component that translates external events to strategy-internal events.

**Responsibilities:**
1. **Subscribe** to `APL_*` events (platform scope)
2. **Initialize** strategy run via `StrategyCache.start_new_run()`
3. **Transform** event: remove `APL_` prefix
4. **Publish** internal event (strategy scope)

**Event Transformation:**
```
Input (PLATFORM):        Output (STRATEGY):
APL_CANDLE_CLOSE_1H  →   CANDLE_CLOSE_1H
APL_NEWS_EVENT       →   NEWS_EVENT
APL_DAILY_SCHEDULE   →   DAILY_SCHEDULE
APL_ORDER_FILLED     →   ORDER_FILLED
```

**Scope Transition:** `ScopeLevel.PLATFORM` → `ScopeLevel.STRATEGY`

**Configuration (strategy_blueprint.yaml):**
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

**Properties:**
- **Event Adapter:** ✅ Per strategy instance
- **Scope:** PLATFORM (input) → STRATEGY (output)
- **Critical:** `is_critical=False`
- **Side Effect:** `StrategyCache.start_new_run()` (guarantee for workers)

---

### 2.3 Strategy Components (Internal Communication)

**Role:** Strategy workers that communicate internally within **strategy scope**.

**Workers and their Events:**

| Worker | Input Events | Output Events |
|--------|-------------|---------------|
| **SignalDetector** | `CANDLE_CLOSE_1H`, `NEWS_EVENT` | `SIGNAL_DETECTED`, `OPPORTUNITY_IDENTIFIED` |
| **RiskEvaluator** | `SIGNAL_DETECTED`, `OPPORTUNITY_IDENTIFIED` | `RISK_ASSESSED`, `THREAT_DETECTED` |
| **EntryPlanner** | `RISK_ASSESSED` | `ENTRY_PLAN_READY` |
| **PositionSizer** | `ENTRY_PLAN_READY` | `POSITION_SIZED` |
| **OrderRouter** | `POSITION_SIZED` | `ORDER_PLACED`, `ORDER_ROUTING_FAILED` |
| **ExecutionMonitor** | `ORDER_FILLED`, `ORDER_CANCELLED` | `EXECUTION_COMPLETE`, `EXECUTION_FAILED` |
| **FlowTerminator** | `EXECUTION_COMPLETE`, `EXECUTION_FAILED` | None (side effect: `StrategyCache.clear_cache()`) |

**Properties:**
- **Event Adapter:** ✅ Per worker instance
- **Scope:** `ScopeLevel.STRATEGY` with **required** `strategy_instance_id`
- **Critical:** `is_critical=False` (strategy failures are isolated)
- **Isolation:** Strategy A events are never visible to Strategy B

---

### 2.4 Platform Monitors (Observing Strategies)

**Role:** Platform singletons that **monitor all strategies** without interfering.

| Monitor | Subscribes To | Action | Output |
|---------|---------------|--------|--------|
| **PerformanceMonitor** | `EXECUTION_COMPLETE` (all strategies) | Calculate P&L, Sharpe ratio, drawdown | Metrics to dashboard |
| **AuditLogger** | All strategy events (wildcard) | Persist to audit database | Audit logs for compliance |
| **AlertManager** | `THREAT_DETECTED`, `EXECUTION_FAILED` | Generate user alerts | Email/SMS/Telegram |
| **RiskAggregator** | `POSITION_SIZED`, `RISK_ASSESSED` (all strategies) | Aggregate cross-strategy risk | Portfolio risk metrics |

**Properties:**
- **Event Adapter:** ✅ Singleton per platform component
- **Scope Filter:** `SubscriptionScope(level=STRATEGY, strategy_instance_id=None)` (all strategies)
- **Critical:** `is_critical=False` (monitoring failures not fatal)
- **Read-Only:** Observe only, no strategy state modification

---

### 2.5 Platform ↔ Strategy Communication (Bidirectional)

**Role:** Platform services that **interact with** strategies (not just observe).

#### Platform → Strategy

| Component | Event | Action | Use Case |
|-----------|-------|--------|----------|
| **ResourceManager** | `APL_RESOURCE_LIMIT_REACHED` | Strategy FlowInitiator receives → pauses strategy | RAM/CPU limits, rate limiting |
| **MaintenanceScheduler** | `APL_MAINTENANCE_STARTING` | Strategies receive → graceful shutdown | System upgrades, database backups |

#### Strategy → Platform

| Component | Event | Subscriber | Use Case |
|-----------|-------|------------|----------|
| **OrderRouter** (worker) | `ORDER_PLACED` | ExchangeConnector | Live trading execution |
| **PositionManager** (worker) | `POSITION_CLOSED` | AccountingService | Portfolio management |

**Properties:**
- **Scope:** Mixed (PLATFORM or STRATEGY depending on direction)
- **Critical:** `is_critical=False`
- **Two-Way:** Both publish and subscribe

---

### 2.6 Platform Components (Internal Coordination)

**Role:** Platform singletons that **coordinate internally** for system-level operations.

| Component | Publishes | Subscribers | Action | Use Case |
|-----------|-----------|-------------|--------|----------|
| **ConfigManager** | `CONFIG_UPDATED` | ComponentRegistry, WorkerFactory | Reload manifests, rebuild | Hot-reload configuration |
| **HealthMonitor** | `COMPONENT_FAILED` | AutoRecovery | Start recovery procedures | Self-healing architecture |
| **ResourceAllocator** | `RESOURCE_FREED` | SchedulerService | Schedule queued strategies | Resource optimization |

**Properties:**
- **Event Adapter:** ✅ Singleton per component
- **Scope:** `ScopeLevel.PLATFORM` (singleton communication)
- **Critical:** `is_critical=True` ⚠️ (failures crash system)
- **System-Level:** Infrastructure events, not strategy-related

---

## 3. Event Scoping - Isolation & Filtering

### 3.1 ScopeLevel Enum

```python
# backend/core/interfaces/eventbus.py

class ScopeLevel(str, Enum):
    """Event scope levels for isolation."""
    PLATFORM = "PLATFORM"   # Broadcast to all strategies
    STRATEGY = "STRATEGY"   # Isolated within strategy instance
```

### 3.2 SubscriptionScope Rules

**Platform Scope Subscribe (broadcast receivers):**
```python
# Platform component subscribes to platform events
scope = SubscriptionScope(
    level=ScopeLevel.PLATFORM,
    strategy_instance_id=None  # Not applicable
)
# Receives: All PLATFORM scope publishes
```

**Strategy Scope Subscribe (isolated receiver):**
```python
# Worker subscribes within own strategy
scope = SubscriptionScope(
    level=ScopeLevel.STRATEGY,
    strategy_instance_id="STR_ABC_INSTANCE_001"
)
# Receives: Only events with matching strategy_instance_id
```

**Cross-Strategy Monitor (observe all strategies):**
```python
# Platform monitor subscribes to all strategies
scope = SubscriptionScope(
    level=ScopeLevel.STRATEGY,
    strategy_instance_id=None  # Wildcard: all strategies
)
# Receives: All STRATEGY scope publishes (any strategy_instance_id)
```

### 3.3 Publish Requirements

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

## 4. Event Naming Conventions

### 4.1 Platform Events (External Sources)

**Pattern:** `APL_{SOURCE}_{EVENT_TYPE}` (Application/Platform prefix)

**Examples:**
- Market Data: `APL_CANDLE_CLOSE_1H`, `APL_TICK_BID`, `APL_ORDERBOOK_SNAPSHOT`
- News: `APL_NEWS_ARTICLE`, `APL_EARNINGS_REPORT`
- Time: `APL_DAILY_SCHEDULE`, `APL_HOURLY_SCHEDULE`
- Exchange: `APL_ORDER_FILLED`, `APL_POSITION_UPDATED`

### 4.2 Strategy-Internal Events

**Pattern:** `{EVENT_TYPE}` (no prefix, no suffix)

**FlowInitiator Transformation:**
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

### 4.3 Platform Management Events

**Pattern:** `{COMPONENT}_{ACTION}` (no APL_ prefix)

**Examples:**
- Config: `CONFIG_UPDATED`, `CONFIG_RELOAD_REQUESTED`
- Health: `COMPONENT_FAILED`, `COMPONENT_RECOVERED`
- Resources: `RESOURCE_FREED`, `RESOURCE_LIMIT_REACHED`

---

## 5. Event Adapter Mapping - Complete Overview

| Component | Type | Event Adapter | Scope | Critical |
|-----------|------|---------------|-------|----------|
| **External Sources** |
| OhlcvProvider | Platform | ✅ | PLATFORM | ❌ |
| TickDataProvider | Platform | ✅ | PLATFORM | ❌ |
| OrderbookProvider | Platform | ✅ | PLATFORM | ❌ |
| NewsProvider | Platform | ✅ | PLATFORM | ❌ |
| SentimentAnalyzer | Platform | ✅ | PLATFORM | ❌ |
| SocialMediaProvider | Platform | ✅ | PLATFORM | ❌ |
| RssFeedConnector | Platform | ✅ | PLATFORM | ❌ |
| WebScraperProvider | Platform | ✅ | PLATFORM | ❌ |
| ExchangeConnector | Platform | ✅ | PLATFORM | ❌ |
| Scheduler | Platform | ✅ | PLATFORM | ❌ |
| **Event Translator** |
| FlowInitiator | Platform | ✅ | PLATFORM → STRATEGY | ❌ |
| **Strategy Workers** |
| SignalDetector | Worker | ✅ | STRATEGY | ❌ |
| RiskEvaluator | Worker | ✅ | STRATEGY | ❌ |
| EntryPlanner | Worker | ✅ | STRATEGY | ❌ |
| PositionSizer | Worker | ✅ | STRATEGY | ❌ |
| OrderRouter | Worker | ✅ | STRATEGY | ❌ |
| ExecutionMonitor | Worker | ✅ | STRATEGY | ❌ |
| FlowTerminator | Platform | ✅ | STRATEGY | ❌ |
| **Platform Monitors** |
| PerformanceMonitor | Platform | ✅ | STRATEGY (listen all) | ❌ |
| AuditLogger | Platform | ✅ | STRATEGY (listen all) | ❌ |
| AlertManager | Platform | ✅ | STRATEGY (listen all) | ❌ |
| RiskAggregator | Platform | ✅ | STRATEGY (listen all) | ❌ |
| **Platform ↔ Strategy** |
| ResourceManager | Platform | ✅ | PLATFORM | ❌ |
| MaintenanceScheduler | Platform | ✅ | PLATFORM | ❌ |
| AccountingService | Platform | ✅ | STRATEGY (listen all) | ❌ |
| **Platform Internal** |
| ConfigManager | Platform | ✅ | PLATFORM | ✅ |
| HealthMonitor | Platform | ✅ | PLATFORM | ✅ |
| ResourceAllocator | Platform | ✅ | PLATFORM | ✅ |

---

## 6. Design Principles

### 6.1 Event Isolation via Scoping

**Platform Scope:** Broadcast events to all strategies
- Use case: Market data, time triggers, news
- No strategy_instance_id required
- FlowInitiator filters relevant events

**Strategy Scope:** Isolated events within strategy instance
- Use case: Worker-to-worker communication
- strategy_instance_id REQUIRED
- Other strategies do NOT see these events

### 6.2 Guaranteed Delivery via EventStore

**At-Least-Once:** Events are ALWAYS persisted before processing
- EventStore.persist() BEFORE EventBus.publish()
- Retry mechanism on failures
- Recovery query on strategy restart

**Idempotency:** Workers must be able to detect duplicates
- StrategyCache.is_event_processed(event_id)
- Metadata in event DTOs (event_id, timestamp)

### 6.3 Backpressure Handling via EventQueue

**Async Processing:** Queues decoupling producers from consumers
- Producers: Platform event sources (high throughput)
- Consumers: Strategy workers (variable throughput)
- Queue maxsize prevents memory overflow

**Configurable Policies:** Strategy-specific backpressure handling
- `drop_oldest`: Real-time strategies (latest data most relevant)
- `drop_newest`: Historical strategies (complete dataset required)
- `block`: Critical events (can cause deadlock)

### 6.4 Observability via Platform Monitors

**Read-Only Monitoring:** Platform components observe without interference
- PerformanceMonitor, AuditLogger, AlertManager
- Subscribe with `strategy_instance_id=None` (all strategies)
- is_critical=False (failures not fatal)

### 6.5 Critical Infrastructure Protection

**Platform Singleton Failures:** System-level crashes on critical component failure
- ConfigManager, HealthMonitor, ResourceAllocator
- is_critical=True (raises CriticalEventHandlerError)
- Rationale: Infrastructure failure = stop everything, not half-broken state

---

## 7. Related Documents

- [Event Persistence](EVENT_PERSISTENCE.md) - EventStore, EventQueue, delivery guarantees, recovery
- [Event-Driven Wiring](EVENT_DRIVEN_WIRING.md) - EventBus, EventAdapter, wiring_map.yaml
- [Platform Components](PLATFORM_COMPONENTS.md) - Platform component inventory
- [Data Flow](DATA_FLOW.md) - DispositionEnvelope, worker communication

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-04 | Team | Initial complete event architecture |
| 2.0 | 2025-11-29 | AI Assistant | Split: conceptual model only, persistence moved to EVENT_PERSISTENCE.md, translated to English |
