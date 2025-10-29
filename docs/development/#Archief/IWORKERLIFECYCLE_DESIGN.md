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
**Input:** BuildSpec (translated from YAML, fully decoupled from config implementation)  
**Output:** Worker instance (not yet functional)

```python
# WorkerFactory creates worker from BuildSpec (NOT WorkerConfig!)
# BuildSpec = machine instructions, completely decoupled from YAML structure
worker = WorkerFactory.build_worker(worker_spec: WorkerBuildSpec)

# Worker is constructed but NOT ready to process
assert worker._cache is None  # No runtime dependencies yet
```

**State:** Worker exists but cannot process events

**Why BuildSpec?** Complete decoupling of code from configuration format. WorkerConfig was a V2 concept that tight-coupled workers to YAML structure. BuildSpecs are translated, validated machine instructions.

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

from typing import Protocol, TYPE_CHECKING
from backend.core.interfaces.strategy_cache import IStrategyCache

if TYPE_CHECKING:
    from backend.core.interfaces.persistence import IPersistence
    from backend.core.interfaces.ledger import IStrategyLedger


class IWorkerLifecycle(Protocol):
    """
    Worker lifecycle management for two-phase initialization.
    
    This protocol separates construction (BuildSpec only) from runtime
    dependency injection, solving circular dependency problems.
    
    Lifecycle Phases:
        1. Construction: Worker created from BuildSpec (config-decoupled)
        2. initialize(): Runtime dependencies injected (cache + capabilities)
        3. Active Processing: Worker processes events via process()
        4. shutdown(): Deterministic cleanup and resource release
    
    Example:
        >>> worker = OpportunityWorker(spec=WorkerBuildSpec(...))
        >>> worker.initialize(
        ...     strategy_cache=cache_instance,
        ...     persistence=persistence_instance  # If requested in manifest
        ... )
        >>> # ... worker processes events ...
        >>> worker.shutdown()
    """
    
    def initialize(
        self,
        strategy_cache: IStrategyCache,
        **capabilities  # persistence, strategy_ledger, aggregated_ledger (optional)
    ) -> None:
        """
        Inject runtime dependencies after construction.
        
        Called by bootstrap orchestrator AFTER all workers are constructed
        but BEFORE event processing starts. This enables workers to access
        StrategyCache for reading/writing DTOs, plus optional capabilities
        requested in worker manifest.
        
        Args:
            strategy_cache: Strategy data access layer (MANDATORY)
            **capabilities: Optional dependencies requested via manifest:
                - persistence (IPersistence): Cross-tick/run state storage
                - strategy_ledger (IStrategyLedger): Read-only trade history
                - aggregated_ledger (IAggregatedLedger): Portfolio-wide ledger
        
        Raises:
            WorkerInitializationError: If initialization fails
        
        Post-conditions:
            - Worker is fully functional and ready to process events
            - Worker can access StrategyCache via self._cache
            - Optional capabilities stored if requested in manifest
        
        Manifest Example:
            >>> # manifest.yaml
            >>> capabilities:
            ...   requires_persistence: true
            ...   requires_strategy_ledger: true
        
        Example:
            >>> worker = ThreatWorker(spec=WorkerBuildSpec(...))
            >>> worker.initialize(
            ...     strategy_cache=cache_instance,
            ...     persistence=persistence_instance
            ... )
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
            - Release all capability references (persistence, ledgers)
            - EventAdapter.unwire() called externally (not worker's job)
            - Log cleanup failures but don't propagate exceptions
        
        Post-conditions:
            - Worker is deactivated and cannot process events
            - All resources released (memory, cache, capability references)
        
        Example:
            >>> worker.shutdown()
            >>> assert worker._cache is None
            >>> assert worker._persistence is None
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

### 1. What Dependencies Does initialize() Inject?

**Decision:** Workers receive IStrategyCache + optional capabilities via initialize()

**Core Dependency:**
- **IStrategyCache** (MANDATORY): All workers get StrategyCache for DTO access/storage

**Optional Capabilities** (requested via manifest):
- **Persistence**: Cross-tick/run state storage (e.g., learning algorithms, cumulative metrics)
- **StrategyLedger**: Read-only access to strategy's trade ledger
- **AggregatedLedger**: Read-only access to portfolio-wide ledger (advanced use cases)

**Pattern:**
```python
def initialize(
    self,
    strategy_cache: IStrategyCache,
    persistence: IPersistence | None = None,
    strategy_ledger: IStrategyLedger | None = None
) -> None:
    self._cache = strategy_cache  # MANDATORY
    self._persistence = persistence  # If requested in manifest
    self._ledger = strategy_ledger  # If requested in manifest
```

**Manifest Example:**
```yaml
# manifest.yaml
capabilities:
  requires_persistence: true   # Worker wants cross-run state
  requires_strategy_ledger: true  # Worker needs historical trades
  requires_aggregated_ledger: false  # Not needed
```

**Why Optional Capabilities?**
- Not all workers need persistence (e.g., stateless indicator calculations)
- Ledger access is read-only and only needed for context (e.g., "did we already trade today?")
- Keeps initialization lightweight for simple workers

**What About Journaling?**
- **OPEN DESIGN QUESTION**: No consensus yet on journal implementation strategy
- **Option 1**: IStrategyJournal injected into workers (workers log directly)
- **Option 2**: StrategyCache + dedicated journaling component at run end
- **Decision Deferred**: This design doc assumes NO journal injection (Phase 1.2)
- **Future Work**: Separate design session needed + DTO development for journal entries

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

**Decision:** IWorkerLifecycle is a Protocol (structural typing), BaseWorker categories use ABC

**Two-Tier Strategy:**

**Tier 1: Protocol (Duck Typing)**
```python
# IWorkerLifecycle = Protocol (no inheritance required)
class IWorkerLifecycle(Protocol):
    def initialize(self, strategy_cache: IStrategyCache, ...) -> None: ...
    def shutdown(self) -> None: ...

# Any class with these methods satisfies protocol
class MyCustomWorker:  # No inheritance!
    def initialize(self, strategy_cache: IStrategyCache) -> None:
        self._cache = strategy_cache
    
    def shutdown(self) -> None:
        self._cache = None

# Type checker validates structural compliance
worker: IWorkerLifecycle = MyCustomWorker()  # ✅ Valid
```

**Tier 2: BaseWorker Categories (Boilerplate Reduction)**
```python
# BaseContextWorker = ABC (reduces boilerplate for category)
class BaseContextWorker(ABC):
    """Base class for Context workers - handles initialization boilerplate."""
    
    def __init__(self, spec: WorkerBuildSpec):
        self._spec = spec
        self._cache: IStrategyCache | None = None
    
    def initialize(self, strategy_cache: IStrategyCache, **kwargs) -> None:
        """Standard initialization - subclasses don't override."""
        if strategy_cache is None:
            raise WorkerInitializationError("StrategyCache required")
        self._cache = strategy_cache
        self._setup_capabilities(**kwargs)  # Handle persistence, ledger, etc.
    
    def shutdown(self) -> None:
        """Standard shutdown - subclasses don't override."""
        self._cache = None
    
    @abstractmethod
    def analyze_context(self, tick_data) -> ContextFactor:
        """Pure quant logic - THIS is what strategy devs implement."""
        ...

# Strategy developer focuses ONLY on quant logic
class EMATrendWorker(BaseContextWorker):
    def analyze_context(self, tick_data) -> ContextFactor:
        # NO boilerplate - just analysis logic!
        ema_fast = calculate_ema(tick_data, 12)
        ema_slow = calculate_ema(tick_data, 26)
        trend = "BULLISH" if ema_fast > ema_slow else "BEARISH"
        return ContextFactor(factor_type="TREND", value=trend)
```

**Why Both?**
- **Protocol**: Type checking, flexibility, no forced inheritance
- **BaseWorker**: DRY principle, 90% of workers use standard patterns
- **Strategy devs focus on quant logic**, not lifecycle management

**Worker Categories** (future BaseWorker ABCs):
- BaseContextWorker
- BaseOpportunityWorker
- BaseThreatWorker
- BasePlanningWorker
- BaseStrategyPlanner

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

# 1. Construct all workers from BuildSpecs (config-decoupled!)
workers = [
    WorkerFactory.build_worker(opp_worker_spec),  # BuildSpec, not YAML!
    WorkerFactory.build_worker(threat_worker_spec),
    WorkerFactory.build_worker(ctx_worker_spec),
]

# 2. Initialize EventBus + StrategyCache
event_bus = EventBus()
strategy_cache = StrategyCache()

# 3. Optional: Initialize capability services (if any worker requested them)
persistence_service = PersistenceService()  # If any manifest has requires_persistence
strategy_ledger = StrategyLedger()  # If any manifest has requires_strategy_ledger

# 4. Initialize workers (inject dependencies based on manifest capabilities)
for worker in workers:
    # Determine which capabilities this worker needs (from manifest)
    capabilities = {}
    
    if worker.manifest.requires_persistence:
        capabilities['persistence'] = persistence_service
    
    if worker.manifest.requires_strategy_ledger:
        capabilities['strategy_ledger'] = strategy_ledger
    
    # Initialize with cache + requested capabilities
    worker.initialize(strategy_cache=strategy_cache, **capabilities)

# 5. Wire workers to EventBus (EventAdapter)
adapters = []
for worker in workers:
    adapter = EventAdapter(worker, event_bus)
    adapter.wire(topics=worker.subscribed_topics())
    adapters.append(adapter)

# 6. Start event processing
event_bus.publish("tick.received", tick_data)

# 7. Shutdown (deterministic cleanup)
for adapter in adapters:
    adapter.unwire()  # Disconnect from EventBus

for worker in workers:
    worker.shutdown()  # Release all resources (cache + capabilities)
```

### StrategyCache Integration

```python
# Worker uses StrategyCache + optional capabilities during processing

class OpportunityWorker:
    def __init__(self, spec: WorkerBuildSpec):
        self._spec = spec
        self._cache: IStrategyCache | None = None
        self._persistence: IPersistence | None = None  # If requested
    
    def initialize(
        self,
        strategy_cache: IStrategyCache,
        **capabilities
    ) -> None:
        self._cache = strategy_cache
        # Extract optional capabilities
        self._persistence = capabilities.get('persistence')
    
    def process(self) -> DispositionEnvelope:
        # Read from TickCache
        context = self._cache.get_context_factor(factor_id)
        
        # Read from cross-run persistence (if capability requested)
        if self._persistence:
            prior_signals = self._persistence.get("opportunity_history")
        
        # Business logic
        signal = self._analyze_opportunity(context)
        
        # Write to TickCache
        self._cache.store_opportunity_signal(signal)
        
        # Write to cross-run persistence (if capability requested)
        if self._persistence:
            self._persistence.set("last_signal", signal)
        
        # Return disposition
        return DispositionEnvelope(
            disposition="PUBLISH",
            event_payload=signal
        )
```

**Capability Use Cases:**

**Persistence (Cross-Tick State):**
```python
# Learning algorithm that needs historical state
class AdaptiveRSIWorker:
    def process(self):
        # Get previous threshold (persisted across runs)
        threshold = self._persistence.get("rsi_threshold", default=70)
        
        # Adapt based on recent performance
        if recent_false_positives > 3:
            threshold = min(threshold + 5, 90)
            self._persistence.set("rsi_threshold", threshold)
```

**StrategyLedger (Historical Context):**
```python
# Worker that avoids overtrading
class DailyLimitWorker:
    def process(self):
        # Check today's trade count from ledger
        today_trades = self._ledger.count_trades_today()
        
        if today_trades >= 3:
            return DispositionEnvelope(disposition="STOP")
        
        # Continue with opportunity analysis
        ...
```

## Open Questions & Future Work

### 1. Strategy Journaling Architecture (DEFERRED)

**Context:** Workers need to log decisions, rejections, and trades for UI analytics.

**Open Questions:**
- Should workers inject IStrategyJournal directly and log during processing?
- OR should StrategyCache accumulate data, then dedicated component logs at run end?
- What DTOs do we need for journal entries? (opportunity_rejected, trade_executed, etc.)

**Decision Status:** NOT DECIDED - requires separate design session + DTO development

**Current Approach:** Phase 1.2 assumes NO journal injection. This can be added as optional capability later.

### 2. Ledger Access Granularity

**Context:** Workers may need read-only access to trade history.

**Open Questions:**
- StrategyLedger (strategy-scoped) vs AggregatedLedger (portfolio-wide)?
- What query capabilities should ledger interfaces expose?
- Should ledger access be filtered by date range / symbol / etc.?

**Decision Status:** DEFERRED - Phase 1.2 defines capability hook, implementation in Phase 2+

### 3. BaseWorker Category Design

**Context:** Need BaseWorker ABCs to reduce boilerplate for 5 worker categories.

**Open Questions:**
- How many BaseWorker variants? (BaseContextWorker, BaseOpportunityWorker, etc.)
- What boilerplate should BaseWorker handle? (initialization, capability setup, shutdown)
- What abstract methods should strategy devs implement? (analyze_context, detect_opportunity, etc.)

**Decision Status:** DEFERRED - Phase 1.3 implementation phase

## Related Documentation

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

**Focus:** Behavior validation with BaseWorker categories

```python
# tests/unit/core/test_base_context_worker.py (Phase 1.3)

def test_initialize_stores_strategy_cache():
    """BaseContextWorker stores StrategyCache after initialize()."""
    spec = WorkerBuildSpec(...)  # BuildSpec, not WorkerConfig!
    worker = ConcreteContextWorker(spec=spec)
    cache = Mock(spec=IStrategyCache)
    
    worker.initialize(strategy_cache=cache)
    
    assert worker._cache is cache


def test_initialize_with_persistence_capability():
    """BaseWorker stores persistence if requested in manifest."""
    spec = WorkerBuildSpec(capabilities={"requires_persistence": True})
    worker = ConcreteWorker(spec=spec)
    cache = Mock(spec=IStrategyCache)
    persistence = Mock(spec=IPersistence)
    
    worker.initialize(strategy_cache=cache, persistence=persistence)
    
    assert worker._cache is cache
    assert worker._persistence is persistence


def test_initialize_raises_if_cache_none():
    """BaseWorker raises WorkerInitializationError if cache is None."""
    spec = WorkerBuildSpec(...)
    worker = ConcreteWorker(spec=spec)
    
    with pytest.raises(WorkerInitializationError):
        worker.initialize(strategy_cache=None)


def test_shutdown_releases_all_references():
    """BaseWorker releases cache + capabilities during shutdown()."""
    spec = WorkerBuildSpec(capabilities={"requires_persistence": True})
    worker = ConcreteWorker(spec=spec)
    cache = Mock(spec=IStrategyCache)
    persistence = Mock(spec=IPersistence)
    worker.initialize(strategy_cache=cache, persistence=persistence)
    
    worker.shutdown()
    
    assert worker._cache is None
    assert worker._persistence is None
```

## Related Documentation

- **EventBus Design:** [EVENTBUS_DESIGN.md](EVENTBUS_DESIGN.md) - Event system integration
- **StrategyCache Design:** [Architecture Docs](../architecture/) - Data access layer
- **TDD Workflow:** [TDD_WORKFLOW.md](../coding_standards/TDD_WORKFLOW.md) - Implementation process
- **Implementation Status:** [IMPLEMENTATION_STATUS.md](../implementation/IMPLEMENTATION_STATUS.md) - Current progress

## Changelog

### 2025-10-29 - Design Corrections
- **WorkerFactory uses BuildSpecs** (not WorkerConfig) - config decoupling
- **Capabilities system**: Persistence, StrategyLedger, AggregatedLedger (manifest-driven)
- **Journal decision deferred**: No consensus yet on IStrategyJournal injection strategy
- **Protocol + BaseWorker tiers**: Duck typing for flexibility, ABC for boilerplate reduction
- **V2 migration removed**: V2 is brainstorm documentation, not concrete implementation
- **Open questions documented**: Journaling, ledger granularity, BaseWorker design

### 2025-10-29 - Design Approved (Initial)
- Initial design document created
- Two-phase initialization pattern defined
- Protocol vs ABC decision documented
- Integration points clarified
- Ready for TDD implementation (Phase 1.2)

