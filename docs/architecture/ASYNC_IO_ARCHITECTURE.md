# AsyncIO Architecture - Event Loop & Timing Design

**Status:** Design  
**Versie:** 1.0  
**Laatst Bijgewerkt:** 2025-11-06

---

## Executive Summary

Dit document definieert hoe **AsyncIO** wordt toegepast in SimpleTraderV3 om **event-driven I/O** en **timing configuratie** te beheren. Het design volgt de **Single Responsibility Principle**: AsyncIO voor I/O, timing geconfigureerd onafhankelijk van business logic.

**Kernprincipes:**
- **AsyncIO ALLEEN voor I/O-bound operaties** (network, database, file I/O)
- **Timing volledig gescheiden van business logic** (pure timing configuration layer)
- **Event-driven state updates** (observers poll state, geen complex request-response)
- **Sequential processing per strategy** (events processed FIFO binnen strategy)
- **Parallel strategies** (strategies run in separate async loops)

**Geen Thread Pools (voorlopig):** CPU-intensive work blijft in async loop tot bottleneck bewezen.

---

## Doelstellingen

### 1. I/O Efficiency

**Probleem:** Blocking I/O blokkeert hele applicatie tijdens wachten op external resources.

**Oplossing:** AsyncIO event loop multiplext I/O operaties zonder threads.

**Use Cases:**
- **Data Connectors:** Exchange API calls, RSS feeds, webhooks (network I/O)
- **Database Access:** Event persistence, query execution (database I/O)  
- **EventBus:** Async event routing (in-memory, maar async pattern)

**Voordeel:**
- 1000+ concurrent connections met 1 thread (vs 1000 threads)
- No GIL contention (single-threaded)
- Minimal memory overhead (coroutines vs thread stacks)

### 2. Timing Separation

**Probleem:** Timing parameters verspreid over code en config (SRP violation).

**Oplossing:** Centraal timing configuration systeem, volledig gescheiden van business logic.

**Timing Concerns:**
- Event intervals (connector fetch frequencies)
- Timeouts (API calls, worker processing)
- Retry delays (backoff policies)
- Monitoring thresholds (slow operation detection)

**Voordeel:**
- Runtime tuning (development vs production policies)
- A/B testing timing parameters
- Single source of truth voor alle timeouts

### 3. Event-Driven Coordination

**Probleem:** Complex request-response coordinatie tussen components (ExecutionGateway anti-pattern).

**Oplossing:** Event-driven state pattern (publishers update state, consumers poll state).

**Pattern:**
```
State Publisher (FlashCrashDetector):
  → Monitors market
  → Publishes: FLASH_CRASH_DETECTED event
  → Updates: Internal state flag

State Consumer (OrderRouter):
  → Polls: ThreatRegistry.is_safe_to_execute()
  → Decides: Execute or skip based on state
```

**Voordeel:**
- No coordination overhead (instant state lookup vs 50-500ms validation)
- No race conditions (state updated before consumers read)
- Extensible (add threat monitors without changing consumers)

---

## Waar Passen We AsyncIO Toe?

### Component Categorization

| Component Type | Async/Sync | Reden |
|----------------|------------|-------|
| **Data Connectors** | Native AsyncIO | I/O-bound (network calls) |
| **EventBus** | Native AsyncIO | Routing + async event dispatch |
| **FlowInitiator** | Native AsyncIO | Lightweight transformation |
| **Strategy Workers** | Native AsyncIO | Sequential processing (no threads needed yet) |
| **Platform Singletons** | Native AsyncIO | Lightweight aggregation |
| **Database Access** | Native AsyncIO | I/O-bound (database queries) |

**Geen Thread Pools:**
- CPU work runs in async loop (blocks temporarily)
- Only probleem als: `processing_time > interval_time`
- Current estimate: 150ms processing, 60s interval → 99.7% idle
- **YAGNI:** Add thread pools later if profiling shows bottleneck

---

## Hoe Passen We AsyncIO Toe?

### 1. Platform Entry Point - Event Loop Orchestration

**Verantwoordelijkheid:** Start AsyncIO event loop en orkestreer alle async components.

**Design:**
```
SimpleTraderPlatform (Main Process)
├── AsyncIO Event Loop (single thread)
│   ├── Data Connectors (async tasks)
│   │   ├── OhlcvProvider.run() (async I/O loop)
│   │   ├── NewsProvider.run() (async I/O loop)
│   │   └── Scheduler.run() (async timer loop)
│   │
│   ├── Strategy Workers (async tasks)
│   │   ├── Strategy_001.run() (async event processing loop)
│   │   ├── Strategy_002.run() (async event processing loop)
│   │   └── Strategy_003.run() (async event processing loop)
│   │
│   └── Platform Singletons (async tasks)
│       ├── ThreatRegistry (event listener)
│       ├── PerformanceMonitor (event listener)
│       └── AuditLogger (event listener)
│
└── Platform State (sync data structures)
    ├── ThreatRegistry._active_threats (dict)
    ├── EventBus._subscriptions (dict)
    └── StrategyCache._tick_caches (dict)
```

**Implementation Location:** `backend/assembly/platform.py`

**Key Pattern:**
- ONE `asyncio.run()` call (entry point)
- `asyncio.gather()` voor parallel component startup
- Shared state accessed synchronously (no locks needed - single threaded)

**Integration met Existing Code:**
- Wraps existing `SimpleTraderPlatform` bootstrap
- Workers blijven interface-compatibel
- EventBus blijft sync-compatible (async wrapper indien nodig)

---

### 2. Data Connectors - Pure Async I/O

**Verantwoordelijkheid:** Fetch data from external sources, publish to EventBus.

**Async Pattern:**
```
OhlcvProvider.run():
  while True:
    # ASYNC I/O (yields to event loop)
    data = await session.get(api_url, timeout=timeout)
    
    # Parse (lightweight CPU work)
    event = parse_candle(data)
    
    # Publish (instant - in-memory queue)
    await event_bus.publish("APL_CANDLE_CLOSE_1H", event)
    
    # Wait interval (yields to event loop)
    await asyncio.sleep(interval)
```

**Why AsyncIO Perfect:**
- Network I/O dominant (API calls 10-100ms)
- Parse/publish negligible (<1ms)
- Multiple connectors run concurrently (no blocking)

**Implementation Location:** `backend/connectors/<connector_type>/`

**Interface:**
```python
class IDataConnector(Protocol):
    async def run(self) -> None:
        """Main async loop - fetch and publish."""
    
    async def connect(self) -> None:
        """Establish connection (async I/O)."""
    
    async def disconnect(self) -> None:
        """Close connection (async I/O)."""
```

**Integration:**
- Platform calls `connector.run()` as async task
- Uses `aiohttp.ClientSession` for HTTP
- Uses `asyncpg` for PostgreSQL (EventStore)

---

### 3. EventBus - Async Event Routing

**Verantwoordelijkheid:** Route events between components with async dispatch.

**Current State:** Synchronous EventBus (Phase 1.2 implementation)

**AsyncIO Enhancement:**
```python
class AsyncEventBus:
    async def publish(
        self,
        event_name: str,
        payload: BaseModel,
        scope: ScopeLevel,
        strategy_instance_id: str | None = None
    ) -> None:
        """Publish event with async handler invocation."""
        
        # Find subscribers (sync - instant lookup)
        subscriptions = self._get_subscriptions(event_name, scope, strategy_instance_id)
        
        # Invoke handlers asynchronously
        tasks = []
        for sub in subscriptions:
            task = asyncio.create_task(sub.handler(payload))
            tasks.append(task)
        
        # Wait for all handlers (non-blocking for other events)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
```

**Why AsyncIO Beneficial:**
- Handlers can be async (await database writes, API calls)
- Multiple handlers run concurrently
- No blocking during handler execution

**Implementation Location:** `backend/core/eventbus.py`

**Migration Strategy:**
- Keep sync `publish()` for backward compatibility
- Add async `publish_async()` for new code
- Gradually migrate handlers to async

---

### 4. FlowInitiator - Async Event Transformation

**Verantwoordelijkheid:** Transform platform events to strategy events, initialize runs.

**Async Pattern:**
```python
class FlowInitiator:
    async def on_platform_event(self, event: BaseModel) -> None:
        """Transform platform event (async)."""
        
        # Initialize run (sync - lightweight)
        self.strategy_cache.start_new_run(RunAnchor(...))
        
        # Transform event (sync - instant)
        strategy_event = self._transform_event(event)
        
        # Publish to strategy scope (async)
        await self.event_bus.publish(
            event_name=strategy_event.event_name,
            payload=strategy_event,
            scope=ScopeLevel.STRATEGY,
            strategy_instance_id=self.strategy_id
        )
```

**Why AsyncIO Appropriate:**
- EventBus publish is async
- Lightweight transformation (no heavy computation)
- Multiple FlowInitiators run concurrently (one per strategy)

**Implementation Location:** `backend/core/flow_initiator.py`

---

### 5. Strategy Workers - Sequential Async Processing

**Verantwoordelijkheid:** Process events from queue, publish results.

**Async Pattern:**
```python
class StrategyWorkerBase:
    async def run(self) -> None:
        """Main processing loop (sequential)."""
        while True:
            # Wait for next event (async - yields if empty)
            event = await self._event_queue.get()
            
            # Process with timeout (async wrapper)
            try:
                result = await asyncio.wait_for(
                    self.process_event(event),
                    timeout=self._timeout
                )
                
                # Publish result (async)
                if result:
                    await self.event_bus.publish(
                        event_name=result.event_name,
                        payload=result.payload,
                        scope=ScopeLevel.STRATEGY,
                        strategy_instance_id=self.strategy_id
                    )
            
            except asyncio.TimeoutError:
                logger.error(f"Worker timeout: {self._timeout}s")
```

**Sequential Guarantee:**
- `await` blocks worker loop until event processed
- Next event only dequeued after previous completes
- Preserves pipeline order within strategy

**Parallel Strategies:**
- Each strategy has own async loop
- Strategy A and B process concurrently
- No blocking between strategies

**Why AsyncIO Sufficient:**
- Processing time (150ms) << interval (60s)
- 99.7% idle time available for other strategies
- EventBus operations async (non-blocking)

**Implementation Location:** `backend/core/strategy_worker_base.py`

**Subclass Interface:**
```python
async def process_event(self, event: BaseModel) -> Event | None:
    """Override in subclass - async processing."""
    # Can have CPU work (blocks loop temporarily)
    # Use 'await asyncio.sleep(0)' in long loops to yield
```

---

### 6. Platform Singletons - Async State Management

**Verantwoordelijkheid:** Monitor strategies, aggregate metrics, manage state.

**Example: ThreatRegistry (Event-Driven State)**
```python
class ThreatRegistry:
    async def _on_flash_crash_detected(self, payload: dict) -> None:
        """Handle threat detection event (async)."""
        # Update state (sync - instant dict write)
        self._active_threats['flash_crash'] = payload
        
        logger.warning("Threat active: flash_crash")
    
    async def _on_flash_crash_cleared(self, payload: dict) -> None:
        """Handle threat cleared event (async)."""
        # Update state (sync - instant dict delete)
        if 'flash_crash' in self._active_threats:
            del self._active_threats['flash_crash']
        
        logger.info("Threat cleared: flash_crash")
    
    def is_safe_to_execute(self) -> tuple[bool, list[str]]:
        """Synchronous state query (instant)."""
        if not self._active_threats:
            return (True, [])
        
        threat_names = list(self._active_threats.keys())
        return (False, threat_names)
```

**Pattern Benefits:**
- State updates async (event handlers)
- State queries sync (no await needed)
- No race conditions (single-threaded event loop)

**Implementation Location:** `backend/core/threat_registry.py`

---

## Timing Configuration - Complete Separation

### Design Principe: Pure SRP

**Timing is Cross-Cutting Concern:**
- Strategy agnostic (applies to all strategies)
- EventBus agnostic (applies to all components)
- Operation agnostic (network, CPU, database timing)

**Separation:**
```
config/
├── timing.yaml              # PURE timing (intervals, timeouts, retries)
├── event_routing.yaml       # PURE event flow (who subscribes to what)
├── connectors.yaml          # PURE business logic (symbols, APIs, auth)
└── strategies.yaml          # PURE business logic (indicators, parameters)
```

### Timing Configuration Schema

**File:** `config/timing.yaml`

**Structure:**
```yaml
version: "1.0"

# Global timing policies (switch at runtime)
policies:
  development:
    default_interval_ms: 5000
    default_timeout_ms: 30000
    default_retry_delay_ms: 1000
    
  production:
    default_interval_ms: 60000
    default_timeout_ms: 10000
    default_retry_delay_ms: 5000
  
  backtest:
    default_interval_ms: 0        # No wait in backtest
    default_timeout_ms: 60000
    default_retry_delay_ms: 100

active_policy: production

# Component-specific overrides (by ID, not type)
components:
  event_loop:
    tick_interval_ms: 10
    io_poll_timeout_ms: 100
  
  connectors:
    CONN_001:  # OhlcvProvider instance
      interval_ms: 60000
      timeout_ms: 10000
      retry_delay_ms: 5000
      backoff_multiplier: 2.0
    
    CONN_002:  # NewsProvider instance
      interval_ms: 300000
      timeout_ms: 15000
  
  event_bus:
    publish_timeout_ms: 100
    metrics_flush_interval_ms: 10000
  
  workers:
    WORKER_STR001_001:  # Strategy 1, Worker 1
      timeout_ms: 5000
    
    WORKER_STR002_001:  # Strategy 2, Worker 1
      timeout_ms: 3000

# Timeout categories (fallback hierarchy)
timeouts:
  categories:
    network_io:
      default_ms: 10000
    
    cpu_processing:
      default_ms: 5000
    
    database_query:
      default_ms: 1000
  
  resolution_order:
    - component_id     # Most specific
    - category         # Fallback
    - active_policy    # Default

# Monitoring thresholds
monitoring:
  slow_operation_threshold_ms: 100
  stuck_operation_threshold_ms: 5000
  metrics_aggregation_window_ms: 60000
```

### TimingResolver Implementation

**Location:** `backend/core/timing_resolver.py`

**Interface:**
```python
class TimingResolver:
    def __init__(self, config_path: str):
        """Load timing configuration."""
    
    def get_interval(self, component_id: str) -> int:
        """Get interval in milliseconds."""
    
    def get_timeout(
        self,
        component_id: str,
        category: str | None = None
    ) -> int:
        """Get timeout in milliseconds."""
    
    def get_retry_config(self, component_id: str) -> dict:
        """Get retry configuration."""
    
    def switch_policy(self, policy_name: str) -> None:
        """Switch active policy at runtime."""
```

**Usage in Components:**
```python
class OhlcvProvider:
    def __init__(
        self,
        connector_id: str,
        config: dict,           # From connectors.yaml (business logic)
        timing: TimingResolver  # From timing.yaml (pure timing)
    ):
        self.connector_id = connector_id
        self.config = config
        
        # ALL timing from resolver
        self._interval = timing.get_interval(connector_id) / 1000
        self._timeout = timing.get_timeout(connector_id, category='network_io') / 1000
        self._retry_config = timing.get_retry_config(connector_id)
```

**Benefits:**
- Runtime policy switching (development ↔ production)
- A/B testing timing parameters
- No code changes for timing adjustments
- Single source of truth

---

## Event-Driven State Pattern

### Pattern: State Publisher + State Consumer

**Anti-Pattern (Complex Coordination):**
```
OrderRouter → ExecutionGateway → Broadcast validation request
                ↓
           Wait for responses (50-500ms)
                ↓
           Aggregate decisions
                ↓
           Publish approval/veto
                ↓
OrderRouter → Execute or skip
```

**Correct Pattern (Event-Driven State):**
```
FlashCrashDetector → Publish FLASH_CRASH_DETECTED → ThreatRegistry updates state
                                                            ↓
OrderRouter → Poll ThreatRegistry.is_safe_to_execute() → Execute or skip
```

### Implementation: ThreatRegistry

**State Publisher (FlashCrashDetector):**
```python
class FlashCrashDetector(StrategyWorkerBase):
    async def process_event(self, event: CandleCloseEvent) -> Event | None:
        """Detect flash crash (lightweight)."""
        
        # Calculate metrics (fast - <10ms)
        volatility = self._calculate_volatility(event)
        price_drop = self._calculate_price_drop(event)
        
        # Determine state
        flash_crash_now = (volatility > 5.0 or price_drop > 0.10)
        
        # State transition?
        if flash_crash_now and not self._flash_crash_active:
            self._flash_crash_active = True
            
            return Event(
                event_name="APL_FLASH_CRASH_DETECTED",
                payload={"volatility": volatility, "price_drop": price_drop}
            )
        
        elif not flash_crash_now and self._flash_crash_active:
            self._flash_crash_active = False
            
            return Event(
                event_name="APL_FLASH_CRASH_CLEARED",
                payload={}
            )
        
        return None
```

**State Registry (ThreatRegistry):**
```python
class ThreatRegistry:
    def __init__(self, event_bus):
        self._active_threats: dict[str, dict] = {}
        
        # Subscribe to threat events
        event_bus.subscribe("APL_FLASH_CRASH_DETECTED", self._on_flash_crash_detected)
        event_bus.subscribe("APL_FLASH_CRASH_CLEARED", self._on_flash_crash_cleared)
    
    async def _on_flash_crash_detected(self, payload: dict) -> None:
        """Record threat (async event handler)."""
        self._active_threats['flash_crash'] = payload
    
    async def _on_flash_crash_cleared(self, payload: dict) -> None:
        """Clear threat (async event handler)."""
        if 'flash_crash' in self._active_threats:
            del self._active_threats['flash_crash']
    
    def is_safe_to_execute(self) -> tuple[bool, list[str]]:
        """Query state (sync - instant)."""
        if not self._active_threats:
            return (True, [])
        
        threat_names = list(self._active_threats.keys())
        return (False, threat_names)
```

**State Consumer (OrderRouter):**
```python
class OrderRouter(StrategyWorkerBase):
    def __init__(self, ..., threat_registry: ThreatRegistry):
        self.threat_registry = threat_registry
    
    async def process_event(self, event: EntryPlanEvent) -> Event | None:
        """Route order with threat check (async)."""
        
        # Check threats (sync - instant lookup)
        safe, threats = self.threat_registry.is_safe_to_execute()
        
        if not safe:
            logger.warning(f"Skipping execution: {threats}")
            return Event(
                event_name="ORDER_REJECTED_BY_THREAT",
                payload={"threats": threats}
            )
        
        # Create order (sync)
        order = self._create_order(event)
        
        # Submit to exchange (async I/O)
        await self._submit_to_exchange(order)
        
        return Event(
            event_name="ORDER_SUBMITTED",
            payload=order
        )
```

**Benefits:**
- No coordination overhead (instant state lookup vs 50-500ms)
- No race conditions (state updated before consumers read)
- Extensible (add threat monitors without changing consumers)
- Simple reasoning (event-driven state machine)

---

## Integration met Bestaande Architectuur

### 1. EventBus (Existing Component)

**Current:** Synchronous EventBus (Phase 1.2)

**Async Migration:**
```python
# Keep existing sync interface
class EventBus:
    def publish(self, topic: str, payload: dict) -> None:
        """Sync publish (backward compatible)."""
        # Invoke handlers synchronously
    
    # Add async interface
    async def publish_async(
        self,
        event_name: str,
        payload: BaseModel,
        scope: ScopeLevel,
        strategy_instance_id: str | None
    ) -> None:
        """Async publish (new code)."""
```

**Gradual Migration:**
- New components use `publish_async()`
- Existing components use sync `publish()`
- Both coexist during transition

---

### 2. StrategyCache (Existing Component)

**Current:** Synchronous cache access

**Async Compatibility:**
```python
# StrategyCache blijft sync (in-memory operations)
class StrategyCache:
    def set_result_dto(self, dto: BaseModel) -> None:
        """Sync write (instant - in-memory)."""
    
    def get_required_dtos(self, worker: IWorker) -> dict:
        """Sync read (instant - in-memory)."""

# Workers call sync methods (no await needed)
class SignalDetector(StrategyWorkerBase):
    async def process_event(self, event: CandleCloseEvent) -> Event | None:
        # Sync cache access (instant - no await)
        dtos = self.strategy_cache.get_required_dtos(self)
        
        # Process (CPU work in async loop)
        signal = self._detect_signal(dtos)
        
        return signal
```

**Why Sync Sufficient:**
- StrategyCache is in-memory (no I/O)
- Operations are instant (<1ms)
- No benefit from async overhead

---

### 3. Workers (Plugin Architecture)

**Current:** Sync worker interface

**Async Enhancement:**
```python
# Base class provides async scaffolding
class StrategyWorkerBase:
    async def run(self) -> None:
        """Async event loop (framework code)."""
        while True:
            event = await self._event_queue.get()
            await self._process_event(event)
    
    @abstractmethod
    async def process_event(self, event: BaseModel) -> Event | None:
        """Subclass implements (can be sync or async)."""
        pass

# Workers can stay sync (wrapped in async)
class SignalDetector(StrategyWorkerBase):
    async def process_event(self, event: CandleCloseEvent) -> Event | None:
        # Sync code (no await inside)
        signal = self._detect_signal(event)
        return signal
```

**Migration Path:**
- Existing workers: Add `async def` (no await needed yet)
- New workers: Use async patterns if beneficial
- No breaking changes (sync code runs in async function)

---

### 4. Data Connectors (New Components)

**Full Async Implementation:**
```python
class OhlcvProvider:
    async def run(self) -> None:
        """Async I/O loop."""
        async with aiohttp.ClientSession() as session:
            while True:
                # Async I/O
                candle = await self._fetch_candle(session)
                
                # Publish (async)
                await self.event_bus.publish_async(...)
                
                # Wait (async)
                await asyncio.sleep(self._interval)
```

**Implementation:** New code, no migration needed

---

## Performance Characteristics

### AsyncIO Overhead

**Event Loop Tick:** ~10μs per iteration  
**Task Switch:** ~100ns per `await`  
**Queue Operations:** <1μs per enqueue/dequeue

**Comparison:**
- Thread context switch: 1-10μs (10-100x slower)
- Process context switch: 10-100μs (100-1000x slower)

**Conclusion:** AsyncIO overhead negligible vs I/O latency (10-100ms)

---

### Scalability Limits

**Single Event Loop:**
- Max throughput: ~10,000 events/sec
- Max concurrent tasks: ~10,000 coroutines
- Memory: ~1KB per coroutine

**SimpleTraderV3 Load:**
- Events: ~0.02/sec (60s candles)
- Strategies: 3 simultaneous
- Connectors: 5-10 sources

**Conclusion:** Single event loop sufficient for 1000x current load

---

### When to Add Thread Pool

**Threshold:**
```
IF processing_time > interval_time:
    # Events stack up in queue
    # Add thread pool for CPU work
```

**Current Estimate:**
```
Processing time: 150ms
Interval: 60,000ms
Utilization: 150ms / 60,000ms = 0.25%

Conclusion: 99.75% idle time → NO thread pool needed
```

**Future Addition:**
- Change ONLY `StrategyWorkerBase._process_event()`
- Add `run_in_executor()` wrapper
- No changes to worker implementations

---

## Implementation Roadmap

### Phase 1: Core Infrastructure

**Deliverables:**
1. `AsyncEventBus` - Async event routing
2. `TimingResolver` - Timing configuration system
3. `timing.yaml` - Pure timing configuration schema
4. Platform entry point with `asyncio.run()`

**Status:** Design complete, ready for implementation

---

### Phase 2: Data Connectors

**Deliverables:**
1. `IDataConnector` protocol (async interface)
2. `OhlcvProvider` implementation (aiohttp)
3. `NewsProvider` implementation (aiohttp + feedparser)
4. `Scheduler` implementation (async timers)

**Status:** Design complete, awaiting Phase 1

---

### Phase 3: Worker Migration

**Deliverables:**
1. `StrategyWorkerBase` async scaffolding
2. Worker interface migration (`async def process_event`)
3. EventBus integration (async publish)
4. StrategyCache compatibility (sync access in async context)

**Status:** Design complete, awaiting Phase 2

---

### Phase 4: Platform Singletons

**Deliverables:**
1. `ThreatRegistry` (event-driven state)
2. `PerformanceMonitor` (async event listener)
3. `AuditLogger` (async event listener)

**Status:** Design complete, awaiting Phase 3

---

## Testing Strategy

### Unit Tests

**AsyncIO Patterns:**
```python
import pytest

@pytest.mark.asyncio
async def test_async_event_bus_publish():
    """Test async event publishing."""
    event_bus = AsyncEventBus()
    events_received = []
    
    async def handler(payload):
        events_received.append(payload)
    
    event_bus.subscribe("test.event", handler)
    
    await event_bus.publish_async("test.event", {"data": "test"})
    
    assert len(events_received) == 1
    assert events_received[0]["data"] == "test"
```

**Timing Tests:**
```python
def test_timing_resolver_hierarchy():
    """Test timing resolution hierarchy."""
    timing = TimingResolver("config/timing.yaml")
    
    # Component-specific override
    assert timing.get_timeout("CONN_001") == 10000
    
    # Category fallback
    assert timing.get_timeout("UNKNOWN", category="network_io") == 10000
    
    # Policy default
    assert timing.get_timeout("UNKNOWN") == 10000  # production policy
```

---

### Integration Tests

**End-to-End Async Flow:**
```python
@pytest.mark.asyncio
async def test_connector_to_worker_flow():
    """Test complete async flow from connector to worker."""
    
    # Setup
    event_bus = AsyncEventBus()
    timing = TimingResolver("config/timing.yaml")
    
    # Create components
    connector = OhlcvProvider("CONN_001", config, timing, event_bus)
    worker = SignalDetector("WORKER_001", config, timing, event_bus)
    
    # Start components
    connector_task = asyncio.create_task(connector.run())
    worker_task = asyncio.create_task(worker.run())
    
    # Wait for event processing
    await asyncio.sleep(1.0)
    
    # Verify
    # ... assertions
    
    # Cleanup
    connector_task.cancel()
    worker_task.cancel()
```

---

## Related Documentation

- **Event Architecture:** [EVENT_ARCHITECTURE.md](EVENT_ARCHITECTURE.md)
- **Core Principles:** [CORE_PRINCIPLES.md](CORE_PRINCIPLES.md)
- **Worker Taxonomy:** [WORKER_TAXONOMY.md](WORKER_TAXONOMY.md)
- **Platform Components:** [PLATFORM_COMPONENTS.md](PLATFORM_COMPONENTS.md)

---

## Design Decisions

### 1. No Thread Pools (YAGNI)

**Rationale:** CPU work (150ms) << interval (60s) → 99.7% idle  
**Future:** Add thread pools only when profiling shows bottleneck  
**Benefit:** Simplicity, maintainability

### 2. Pure Timing Configuration (SRP)

**Rationale:** Timing is cross-cutting concern, independent of business logic  
**Benefit:** Runtime tuning, A/B testing, single source of truth

### 3. Event-Driven State (vs Request-Response)

**Rationale:** State polling (instant) vs coordination (50-500ms overhead)  
**Benefit:** No race conditions, extensible, simple reasoning

### 4. Sync StrategyCache (No Async Needed)

**Rationale:** In-memory operations (<1ms), no I/O benefit from async  
**Benefit:** Simplicity, no async overhead

### 5. Gradual EventBus Migration

**Rationale:** Backward compatibility during transition  
**Benefit:** Incremental migration, no breaking changes

---

**Document Einde**
