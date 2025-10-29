# IWorkerLifecycle Protocol Design - Two-Phase Initialization

**Status:** Design Approved  
**Implementation Phase:** Phase 1.2 (Core Protocols)  
**Created:** 2025-10-29  
**TDD Branch:** `feature/worker-lifecycle-protocol`

## Overview

IWorkerLifecycle defines a **two-phase initialization pattern** for all workers in S1mpleTrader V3. This protocol solves V2's circular dependency problems by separating construction from runtime dependency injection, enabling deterministic resource management and proper cleanup.

## Architecture Context

### The V2 Problem: Constructor Injection Hell

```python
# V2 Pattern (PROBLEMATIC)
class V2Worker:
    def __init__(
        self,
        config: WorkerConfig,
        event_bus: EventBus,           # ❌ Circular dependency
        persistor: DatabasePersistor,  # ❌ Requires DB connection
        logger: Logger                 # ❌ Requires full setup
    ):
        self._config = config
        self._event_bus = event_bus
        self._persistor = persistor
        self._logger = logger
```

**Problems:**
1. **Circular Dependencies**: EventBus needs workers, workers need EventBus
2. **Forced Ordering**: Must construct ALL infrastructure before ANY worker
3. **No Cleanup Contract**: No standardized shutdown → memory leaks
4. **Testing Nightmare**: Must mock 5+ dependencies per worker

### The V3 Solution: Two-Phase Initialization

```python
# V3 Pattern (CLEAN)
class V3Worker:
    def __init__(self, config: WorkerConfig):
        """Phase 1: Construction - config only."""
        self._config = config
        self._cache: IStrategyCache | None = None
    
    def initialize(self, strategy_cache: IStrategyCache) -> None:
        """Phase 2: Runtime dependency injection."""
        self._cache = strategy_cache
    
    def shutdown(self) -> None:
        """Phase 3: Deterministic cleanup."""
        # EventAdapter.unwire() called externally
        self._cache = None
```

**Benefits:**
1. **No Circular Dependencies**: Workers constructed first, dependencies injected later
2. **Flexible Bootstrap**: Can construct workers in any order
3. **Standardized Lifecycle**: All workers follow same init/shutdown pattern
4. **Easy Testing**: Mock just StrategyCache, not EventBus

## Worker Lifecycle Phases

### Phase 1: Construction (WorkerFactory)

**Who:** WorkerFactory  
**When:** Bootstrap / Strategy activation  
**Input:** Configuration only (WorkerConfig)  
**Output:** Worker instance (not yet functional)

```python
# WorkerFactory creates worker with config
worker = OpportunityWorker(config=WorkerConfig(...))

# Worker is constructed but NOT ready to process
assert worker._cache is None  # No runtime dependencies yet
```

**State:** Worker exists but cannot process events

### Phase 2: Initialization (IWorkerLifecycle.initialize)

**Who:** Bootstrap orchestrator (OperationService)  
**When:** After ALL workers constructed, before processing starts  
**Input:** Runtime dependencies (IStrategyCache)  
**Output:** Functional worker ready for event processing

```python
# Bootstrap orchestrator injects dependencies
worker.initialize(strategy_cache=strategy_cache_instance)

# Worker is now FULLY functional
assert worker._cache is not None
```

**State:** Worker ready to process events via `process()`

### Phase 3: Active Processing

**Who:** EventAdapter  
**When:** Events arrive on subscribed topics  
**Input:** Event payload from EventBus  
**Output:** DispositionEnvelope (PUBLISH/PERSIST/IGNORE)

```python
# EventAdapter calls worker.process() when event arrives
envelope = worker.process()

# Worker uses StrategyCache to read/write data
signal = worker._cache.get_opportunity_signal(signal_id)
```

**State:** Worker actively processing events

### Phase 4: Shutdown (IWorkerLifecycle.shutdown)

**Who:** Bootstrap orchestrator (OperationService)  
**When:** Strategy deactivation / system shutdown  
**Input:** None  
**Output:** Clean resource release

```python
# Bootstrap orchestrator triggers cleanup
worker.shutdown()

# Worker releases all resources
assert worker._cache is None
```

**State:** Worker deactivated, resources released

## Protocol Definition

### IWorkerLifecycle Interface

```python
# backend/core/interfaces/worker.py

from typing import Protocol
from backend.core.interfaces.strategy_cache import IStrategyCache


class IWorkerLifecycle(Protocol):
    """
    Worker lifecycle management for two-phase initialization.
    
    This protocol separates construction (config only) from runtime
    dependency injection, solving V2's circular dependency problems.
    
    Lifecycle Phases:
        1. Construction: Worker created with config only
        2. initialize(): Runtime dependencies injected (strategy_cache)
        3. Active Processing: Worker processes events via process()
        4. shutdown(): Deterministic cleanup and resource release
    
    Example:
        >>> worker = OpportunityWorker(config=WorkerConfig(...))
        >>> worker.initialize(strategy_cache=cache_instance)
        >>> # ... worker processes events ...
        >>> worker.shutdown()
    """
    
    def initialize(self, strategy_cache: IStrategyCache) -> None:
        """
        Inject runtime dependencies after construction.
        
        Called by bootstrap orchestrator AFTER all workers are constructed
        but BEFORE event processing starts. This enables workers to access
        StrategyCache for reading/writing signals and plans.
        
        Args:
            strategy_cache: Strategy data access layer
        
        Raises:
            WorkerInitializationError: If initialization fails
        
        Post-conditions:
            - Worker is fully functional and ready to process events
            - Worker can access StrategyCache via self._cache
        
        Example:
            >>> worker = ThreatWorker(config=WorkerConfig(...))
            >>> worker.initialize(strategy_cache=cache_instance)
            >>> # Worker is now ready for event processing
        """
        ...
    
    def shutdown(self) -> None:
        """
        Graceful cleanup and resource release.
        
        Called by bootstrap orchestrator during strategy deactivation or
        system shutdown. Must NEVER raise exceptions - swallow all errors
        and log them instead.
        
        Responsibilities:
            - Release StrategyCache reference (set to None)
            - EventAdapter.unwire() called externally (not worker's job)
            - Log cleanup failures but don't propagate exceptions
        
        Post-conditions:
            - Worker is deactivated and cannot process events
            - All resources released (memory, cache references)
        
        Example:
            >>> worker.shutdown()
            >>> assert worker._cache is None
        """
        ...


class WorkerInitializationError(Exception):
    """
    Raised when worker initialization fails.
    
    Initialization can fail due to:
        - Invalid StrategyCache instance
        - Resource allocation failures
        - Configuration validation errors
    
    Example:
        >>> try:
        ...     worker.initialize(strategy_cache=None)
        ... except WorkerInitializationError as e:
        ...     logger.error(f"Worker init failed: {e}")
    """
    pass
```

## Design Decisions

### 1. Why Only IStrategyCache Dependency?

**Decision:** Workers only receive IStrategyCache, not EventBus/Persistor/Logger

**Rationale:**
- **StrategyCache = Data Access Layer**: All strategy data (signals, plans) lives here
- **EventBus = Infrastructure**: Workers don't call EventBus directly (EventAdapter does)
- **Persistor = Infrastructure**: StrategyCache handles persistence internally
- **Logger = Cross-Cutting**: Workers use module-level logger (not injected)

**Pattern:**
```python
# Worker ONLY needs StrategyCache
def initialize(self, strategy_cache: IStrategyCache) -> None:
    self._cache = strategy_cache  # Only dependency

# EventAdapter handles EventBus wiring
adapter.wire(worker, event_bus)  # Worker doesn't know EventBus exists
```

### 2. Why initialize() Can Raise, shutdown() Cannot?

**Decision:** `initialize()` raises WorkerInitializationError, `shutdown()` never raises

**Rationale:**
- **Initialization = Fail-Fast**: If worker can't start, stop immediately
- **Shutdown = Best-Effort**: During shutdown, swallow errors and log them

**Example:**
```python
def initialize(self, strategy_cache: IStrategyCache) -> None:
    if strategy_cache is None:
        raise WorkerInitializationError("StrategyCache cannot be None")
    self._cache = strategy_cache

def shutdown(self) -> None:
    try:
        # Cleanup logic
        self._cache = None
    except Exception as e:
        logger.error(f"Shutdown error (swallowed): {e}")
        # Don't re-raise - shutdown must never fail
```

### 3. Why Not Pass EventBus to initialize()?

**Decision:** EventBus is NOT passed to worker initialization

**Rationale:**
- **Decoupling**: Workers stay bus-agnostic (easier testing)
- **EventAdapter Owns Wiring**: EventAdapter.wire() handles EventBus subscriptions
- **Separation of Concerns**: Worker = business logic, EventAdapter = infrastructure

**Pattern:**
```python
# Phase 2: Worker initialization (NO EventBus)
worker.initialize(strategy_cache=cache)

# Phase 2.5: EventAdapter wiring (EventBus connection)
adapter = EventAdapter(worker, event_bus)
adapter.wire(topics=["opportunity.*"])
```

### 4. Why Protocol Instead of ABC?

**Decision:** IWorkerLifecycle is a Protocol, not ABC (Abstract Base Class)

**Rationale:**
- **Structural Typing**: Workers don't need to inherit anything
- **Easier Testing**: Can create test doubles without inheritance
- **Flexibility**: Workers can implement multiple protocols independently

**Example:**
```python
# Worker implements IWorkerLifecycle via duck typing
class OpportunityWorker:  # No inheritance needed
    def initialize(self, strategy_cache: IStrategyCache) -> None:
        ...
    
    def shutdown(self) -> None:
        ...

# Type checker validates protocol compliance
def bootstrap_worker(worker: IWorkerLifecycle) -> None:
    worker.initialize(cache)  # ✅ Type-safe
```

## Implementation Phases

### Phase 1.2: Protocol Definition (NOW)

**Deliverables:**
- `backend/core/interfaces/worker.py` - IWorkerLifecycle protocol
- `tests/unit/core/interfaces/test_worker.py` - ~10 protocol tests
- WorkerInitializationError exception

**Tests (~10):**
1. IWorker protocol structure (2 tests)
   - Has `name` property returning str
   - Protocol compliance with structural typing

2. IWorkerLifecycle protocol structure (5 tests)
   - Has `initialize()` method with IStrategyCache parameter
   - Has `shutdown()` method with no parameters
   - `initialize()` can raise WorkerInitializationError
   - `shutdown()` returns None
   - Protocol compliance with structural typing

3. WorkerInitializationError (2 tests)
   - Is Exception subclass
   - Can be instantiated with message

4. Type checking (1 test)
   - IWorkerLifecycle variables accept conforming objects

**Quality Gates:**
- Pylint 10/10 (whitespace, imports, line length)
- Pylance 0 errors/warnings
- 100% tests passing

### Phase 1.3: BaseWorker Implementation (LATER)

**Deliverables:**
- `backend/core/base_worker.py` - Abstract base class
- `tests/unit/core/test_base_worker.py` - ~30 implementation tests

**Tests (~30):**
- Initialization behavior (10 tests)
- Shutdown behavior (5 tests)
- Resource management (5 tests)
- Error handling (5 tests)
- Integration with StrategyCache (5 tests)

### Phase 3: EventAdapter Integration (MUCH LATER)

**Deliverables:**
- `backend/core/event_adapter.py` - EventBus ↔ Worker bridge
- Tests for wire/unwire behavior

## Integration Points

### Bootstrap Orchestration

```python
# OperationService bootstraps workers

# 1. Construct all workers (config only)
workers = [
    OpportunityWorker(config=opp_config),
    ThreatWorker(config=threat_config),
    ContextWorker(config=ctx_config),
]

# 2. Initialize EventBus + StrategyCache
event_bus = EventBus()
strategy_cache = StrategyCache()

# 3. Initialize workers (inject dependencies)
for worker in workers:
    worker.initialize(strategy_cache=strategy_cache)

# 4. Wire workers to EventBus (EventAdapter)
adapters = []
for worker in workers:
    adapter = EventAdapter(worker, event_bus)
    adapter.wire(topics=worker.subscribed_topics())
    adapters.append(adapter)

# 5. Start event processing
event_bus.publish("tick.received", tick_data)

# 6. Shutdown (deterministic cleanup)
for adapter in adapters:
    adapter.unwire()  # Disconnect from EventBus

for worker in workers:
    worker.shutdown()  # Release resources
```

### StrategyCache Integration

```python
# Worker uses StrategyCache during processing

class OpportunityWorker:
    def __init__(self, config: WorkerConfig):
        self._config = config
        self._cache: IStrategyCache | None = None
    
    def initialize(self, strategy_cache: IStrategyCache) -> None:
        self._cache = strategy_cache
    
    def process(self) -> DispositionEnvelope:
        # Read from cache
        context = self._cache.get_context_factor(factor_id)
        
        # Business logic
        signal = self._analyze_opportunity(context)
        
        # Write to cache
        self._cache.store_opportunity_signal(signal)
        
        # Return disposition
        return DispositionEnvelope(
            disposition="PUBLISH",
            event_payload=signal
        )
```

## Testing Strategy

### Protocol Tests (Phase 1.2 - NOW)

**Focus:** Structure validation, NOT behavior

```python
# tests/unit/core/interfaces/test_worker.py

def test_iworker_has_name_property():
    """IWorker protocol requires 'name' property returning str."""
    
    class ValidWorker:
        @property
        def name(self) -> str:
            return "test_worker"
    
    worker: IWorker = ValidWorker()
    assert isinstance(worker.name, str)


def test_iworkerlifecycle_has_initialize_method():
    """IWorkerLifecycle requires initialize(strategy_cache) method."""
    
    class ValidWorker:
        def initialize(self, strategy_cache: IStrategyCache) -> None:
            pass
    
    worker: IWorkerLifecycle = ValidWorker()
    # Protocol compliance check passes


def test_worker_initialization_error_is_exception():
    """WorkerInitializationError is Exception subclass."""
    assert issubclass(WorkerInitializationError, Exception)
```

**NO implementation tests** - those come in Phase 1.3 with BaseWorker

### Implementation Tests (Phase 1.3 - LATER)

**Focus:** Behavior validation with BaseWorker

```python
# tests/unit/core/test_base_worker.py (Phase 1.3)

def test_initialize_stores_strategy_cache():
    """BaseWorker stores StrategyCache reference after initialize()."""
    worker = ConcreteWorker(config=WorkerConfig(...))
    cache = Mock(spec=IStrategyCache)
    
    worker.initialize(strategy_cache=cache)
    
    assert worker._cache is cache


def test_initialize_raises_if_cache_none():
    """BaseWorker raises WorkerInitializationError if cache is None."""
    worker = ConcreteWorker(config=WorkerConfig(...))
    
    with pytest.raises(WorkerInitializationError):
        worker.initialize(strategy_cache=None)


def test_shutdown_releases_cache_reference():
    """BaseWorker sets _cache to None during shutdown()."""
    worker = ConcreteWorker(config=WorkerConfig(...))
    cache = Mock(spec=IStrategyCache)
    worker.initialize(strategy_cache=cache)
    
    worker.shutdown()
    
    assert worker._cache is None
```

## Migration Path (V2 → V3)

### V2 Pattern (OLD)

```python
# V2: Everything via constructor
class V2OpportunityWorker:
    def __init__(
        self,
        config: WorkerConfig,
        event_bus: EventBus,
        persistor: DatabasePersistor,
        logger: Logger
    ):
        self._config = config
        self._event_bus = event_bus
        self._persistor = persistor
        self._logger = logger
        
        # Immediate setup (no two-phase)
        self._setup_resources()
```

### V3 Pattern (NEW)

```python
# V3: Two-phase initialization
class V3OpportunityWorker:
    def __init__(self, config: WorkerConfig):
        """Phase 1: Config only."""
        self._config = config
        self._cache: IStrategyCache | None = None
    
    def initialize(self, strategy_cache: IStrategyCache) -> None:
        """Phase 2: Runtime dependencies."""
        if strategy_cache is None:
            raise WorkerInitializationError("StrategyCache required")
        self._cache = strategy_cache
    
    def shutdown(self) -> None:
        """Phase 3: Cleanup."""
        self._cache = None
```

## Open Questions

None - design approved for implementation.

## Related Documentation

- **EventBus Design:** [EVENTBUS_DESIGN.md](EVENTBUS_DESIGN.md) - Event system integration
- **StrategyCache Design:** [Architecture Docs](../architecture/) - Data access layer
- **TDD Workflow:** [TDD_WORKFLOW.md](../coding_standards/TDD_WORKFLOW.md) - Implementation process
- **Implementation Status:** [IMPLEMENTATION_STATUS.md](../implementation/IMPLEMENTATION_STATUS.md) - Current progress

## Changelog

### 2025-10-29 - Design Approved
- Initial design document created
- Two-phase initialization pattern defined
- Protocol vs ABC decision documented
- Integration points clarified
- Ready for TDD implementation (Phase 1.2)
