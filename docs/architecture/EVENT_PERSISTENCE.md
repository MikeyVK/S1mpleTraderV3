# docs/architecture/EVENT_PERSISTENCE.md
# Event Persistence - S1mpleTraderV3

**Status:** PRELIMINARY
**Version:** 1.0
**Last Updated:** 2025-11-29

---

## Purpose

This document defines the **persistence and durability layer** for the event-driven architecture.

**Target audience:** Developers implementing event storage or recovery mechanisms.

## Scope

**In Scope:**
- EventStore - Persistent storage for all platform events
- EventQueue - Per-strategy async buffering with backpressure handling
- Delivery Guarantees - At-least-once delivery, ordering, idempotency
- Recovery Mechanism - Strategy restart and event replay
- Dead Letter Queue - Failed event handling

**Out of Scope:**
- Event model concepts → See [EVENT_ARCHITECTURE.md](EVENT_ARCHITECTURE.md)
- Event-driven wiring → See [EVENT_DRIVEN_WIRING.md](EVENT_DRIVEN_WIRING.md)

---

## 1. The "Missed Events" Problem

### Scenario 1: Strategy Offline
```
Platform publishes: APL_CANDLE_CLOSE_1H (10:00)
Strategy A: Offline for maintenance
→ Event missed without EventStore ❌
```

### Scenario 2: System Crash
```
Platform publishes: APL_ORDER_FILLED (critical event)
System crashes before handler executed
→ Event missed, trade state inconsistent ❌
```

### Scenario 3: Backpressure
```
Platform publishes: 1000 APL_TICK events/sec
Strategy processing: 100 events/sec
→ Events dropped, data loss ❌
```

---

## 3. Solution: EventStore + Queue Layer

### 3.1 Architecture Layers

```
┌─────────────────────────────────────────────────────────┐
│ External Sources (Platform Scope)                       │
│ - Market APIs, News Feeds, Scheduler                    │
│ - Publish: APL_* events                                 │
└────────────────┬────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────┐
│ EventStore (Persistence Layer)                          │
│ - Persist ALL platform events                           │
│ - Replay capability for recovery                        │
│ - Event versioning for schema evolution                 │
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
│ FlowInitiator (Per-Strategy Translator)                 │
│ - Transform: APL_* → internal events                    │
│ - Initialize: StrategyCache.start_new_run()             │
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
│ Strategy Workers (Internal Events)                      │
│ - Process events from queue                             │
│ - Publish results to EventBus (strategy scope)          │
│ - Idempotent processing (duplicate detection)           │
└─────────────────────────────────────────────────────────┘
```

---

## 4. EventStore Design

**Responsibility:** Persistent storage for all platform events.

### 4.1 Schema

```python
@dataclass
class EventRecord:
    event_id: str              # UUID
    event_name: str            # APL_CANDLE_CLOSE_1H
    timestamp: datetime        # Event timestamp
    scope: ScopeLevel          # PLATFORM or STRATEGY
    strategy_instance_id: str | None  # For STRATEGY scope
    payload: dict              # Serialized Pydantic DTO
    payload_schema_version: int       # For backward compatibility
    created_at: datetime       # Storage timestamp
    processed: bool            # Delivery tracking
    processed_at: datetime | None
    retry_count: int           # Failed delivery tracking
    dead_letter: bool          # DLQ flag
```

### 4.2 Storage Backend

| Environment | Backend | Notes |
|-------------|---------|-------|
| Development | SQLite | `events.db` |
| Production | PostgreSQL | With day/week partitioning |

### 4.3 Operations

```python
class IEventStore:
    def persist(self, event: BaseModel, scope: ScopeLevel, 
                strategy_instance_id: str | None) -> str:
        """Persist event, return event_id."""
    
    def get_unprocessed_events(self, strategy_instance_id: str) -> List[EventRecord]:
        """Query unprocessed events for strategy recovery."""
    
    def mark_processed(self, event_id: str) -> None:
        """Mark event as processed after successful delivery."""
    
    def replay_events(self, strategy_instance_id: str, 
                     from_timestamp: datetime, 
                     to_timestamp: datetime) -> Iterator[EventRecord]:
        """Replay events for backtest or recovery."""
    
    def move_to_dead_letter(self, event_id: str, reason: str) -> None:
        """Move failed event to Dead Letter Queue."""
```

### 4.4 Retention Policy

| Event Type | Retention | Rationale |
|------------|-----------|-----------|
| Platform Events | 30 days | Configurable, sufficient for replay |
| Strategy Events | 7 days | Configurable, shorter lifecycle |
| Dead Letter Queue | 90 days | Compliance requirements |

---

## 5. EventQueue Design

**Responsibility:** Per-strategy async buffering with backpressure handling.

### 5.1 Queue Structure

```python
# Per-strategy queues
strategy_queues: Dict[str, asyncio.Queue[EventRecord]] = {
    "STR_ABC_INSTANCE_001": asyncio.Queue(maxsize=1000),
    "STR_XYZ_INSTANCE_002": asyncio.Queue(maxsize=1000)
}

# Dead Letter Queue (shared)
dead_letter_queue: asyncio.Queue[EventRecord] = asyncio.Queue()
```

### 5.2 Queue Configuration

```yaml
# strategy_blueprint.yaml
runtime:
  event_queue:
    maxsize: 1000          # Max events in queue
    timeout_sec: 30        # Dequeue timeout
    max_retries: 3         # Failed delivery retries
    backpressure_policy: "drop_oldest"  # or "block" or "drop_newest"
```

### 5.3 Backpressure Policies

| Policy | Behavior | Use Case |
|--------|----------|----------|
| `drop_oldest` | Remove oldest event when queue full | Real-time strategies (latest data most relevant) |
| `block` | Block producer until queue has space | Critical events (risk: deadlock) |
| `drop_newest` | Ignore new events when queue full | Historical strategies (complete dataset required) |

### 5.4 Operations

```python
class EventQueueManager:
    def enqueue(self, strategy_instance_id: str, event: EventRecord) -> bool:
        """Enqueue event, return success."""
    
    async def dequeue(self, strategy_instance_id: str) -> EventRecord:
        """Dequeue next event (async, waits if empty)."""
    
    def get_queue_depth(self, strategy_instance_id: str) -> int:
        """Query current queue size."""
    
    def flush_queue(self, strategy_instance_id: str) -> None:
        """Clear queue (for strategy stop)."""
```

---

## 6. Delivery Guarantees

### 6.1 At-Least-Once Delivery

**Flow:**
1. Event persist in EventStore (`processed=False`)
2. Event enqueue in EventQueue
3. Worker processes event
4. Worker commit result
5. EventStore mark processed (`processed=True`)

**On failure between steps 3-5:** Event remains `processed=False` → retry on recovery.

### 6.2 Idempotency Requirement

Workers must be **idempotent** (ignore duplicate events):

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

### 6.3 FIFO Ordering

Events for the **same strategy** are always processed in order:
```
Queue STR_ABC:
  1. APL_CANDLE_CLOSE_1H (10:00)
  2. APL_CANDLE_CLOSE_1H (11:00)  ← Blocked until 1 processed
  3. APL_CANDLE_CLOSE_1H (12:00)  ← Blocked until 2 processed
```

**No ordering guarantee cross-strategy:** Strategy A and Strategy B may process events in different order.

---

## 7. Recovery Mechanism

### 7.1 Strategy Restart Flow

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

### 7.2 Replay for Backtest

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

## 8. Dead Letter Queue (DLQ)

**Role:** Storage for events that **cannot be processed** after max retries.

### 8.1 DLQ Flow

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

### 8.2 DLQ UI

Strategy Builder UI displays DLQ events for manual retry or investigation:

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

## 9. Event Versioning & Schema Evolution

### 9.1 Event DTO Versioning

**Problem:** Event schema changes break old strategy instances.

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

### 9.2 EventStore Schema Tracking

```python
@dataclass
class EventRecord:
    payload_schema_version: int  # Track DTO version
    payload: dict                 # Serialized DTO
```

### 9.3 Deserialization with Versioning

```python
class EventDeserializer:
    def deserialize(self, event_record: EventRecord) -> BaseModel:
        """Deserialize with backward compatibility."""
        
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

### 9.4 Migration Strategy

**Forward Compatibility (old workers → new events):**
```python
class CandleCloseEventV2(BaseModel):
    vwap: float = 0.0  # Default value for old workers
```

**Backward Compatibility (new workers → old events):**
```python
class SignalDetector:
    def on_market_trigger(self, event: CandleCloseEvent) -> DispositionEnvelope:
        # Handle both V1 and V2
        vwap = getattr(event, 'vwap', None)
        if vwap is None:
            vwap = self._calculate_vwap(event)  # Fallback
```

---

## 10. Implementation Roadmap

### Phase 1 (MVP)
- [ ] EventStore implementation (SQLite backend)
- [ ] EventQueue implementation (asyncio.Queue)
- [ ] EventStore UI (replay, DLQ management)
- [ ] Basic recovery mechanism

### Phase 2 (Production)
- [ ] PostgreSQL backend for EventStore
- [ ] Event partitioning (performance)
- [ ] Distributed EventQueue (Redis/RabbitMQ)
- [ ] Advanced replay (time-travel debugging)

### Phase 3 (Enterprise)
- [ ] Event versioning migrations (auto-upgrade)
- [ ] Cross-strategy event correlation (causality tracking)
- [ ] Event analytics dashboard
- [ ] Event-driven alerting (complex event processing)

---

## 11. Related Documents

- [Event Architecture](EVENT_ARCHITECTURE.md) - Conceptual event model, producers/consumers, scoping
- [Event-Driven Wiring](EVENT_DRIVEN_WIRING.md) - EventBus, EventAdapter, wiring_map.yaml
- [Platform Components](PLATFORM_COMPONENTS.md) - Platform component inventory
- [Data Flow](DATA_FLOW.md) - DispositionEnvelope, worker communication

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-29 | AI Assistant | Split from EVENT_ARCHITECTURE.md - persistence layer |
