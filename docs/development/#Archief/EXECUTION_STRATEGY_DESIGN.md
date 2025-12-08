# Execution Strategy Architecture

**Status:** Design  
**Created:** 2025-11-05  
**Version:** 1.0

---

## Executive Summary

EventBus execution mode moet **zero-effort switchable** zijn tussen sync, threaded, async en distributed (Ray) execution. Dit wordt bereikt door **Strategy Pattern** met **Dependency Injection** en **configuration-driven** strategy selection.

**Core Principle:**
> "EventBus routes events. ExecutionStrategy executes handlers. Configuration determines which strategy. Switch = change 1 YAML value."

---

## Problem Statement

### Current EventBus Implementation

```python
# backend/core/eventbus.py (HUIDIGE IMPLEMENTATIE)
class EventBus:
    def _invoke_handler(self, subscription, payload):
        try:
            subscription.handler(payload)  # 🔴 HARDCODED SYNC EXECUTION
        except Exception as e:
            # error handling...
```

**Problemen:**
1. ❌ EventBus kent execution mode (SRP violation)
2. ❌ Switching requires code changes (not config-driven)
3. ❌ Testing different modes = modify EventBus code
4. ❌ No gradual rollout (can't test Ray for 1 worker)

### Requirements

1. ✅ **Zero-effort switch**: Change 1 YAML value, restart, done
2. ✅ **SRP**: EventBus routes, Strategy executes
3. ✅ **Per-worker control**: Worker X uses Ray, Worker Y uses sync
4. ✅ **Backward compatible**: Default = current sync behavior
5. ✅ **Testable**: Mock ExecutionStrategy for tests
6. ✅ **Performance metrics**: Track execution stats per strategy

---

## Architecture Design

### IExecutionStrategy Protocol

```python
# backend/core/interfaces/execution_strategy.py

from typing import Protocol, Callable, Any
from pydantic import BaseModel

class IExecutionStrategy(Protocol):
    """
    Handler execution strategy abstraction.
    
    Implementations:
    - SyncExecutionStrategy (current behavior)
    - ThreadPoolExecutionStrategy (flash crash protection)
    - RayExecutionStrategy (ML workers, distributed)
    - AsyncIOExecutionStrategy (I/O bound workers)
    
    Responsibilities:
    - Execute handler with payload
    - Handle exceptions according to is_critical flag
    - Track execution metrics (optional)
    
    NOT responsible for:
    - Event routing (EventBus responsibility)
    - Scope filtering (EventBus responsibility)
    - Subscription management (EventBus responsibility)
    """
    
    def execute(
        self,
        handler: Callable[[BaseModel], Any],
        payload: BaseModel,
        subscription_id: str,
        is_critical: bool
    ) -> None:
        """
        Execute handler with payload.
        
        Args:
            handler: Callable to execute (sync or async)
            payload: Event payload (Pydantic DTO)
            subscription_id: For error tracking
            is_critical: Error handling mode
                - True: Raise exception (crash platform)
                - False: Log error, continue
        
        Raises:
            CriticalEventHandlerError: If is_critical=True and handler fails
        
        Implementation Notes:
        - May execute synchronously (SyncExecutionStrategy)
        - May execute asynchronously (ThreadPoolExecutionStrategy, AsyncIO)
        - May execute remotely (RayExecutionStrategy)
        - MUST handle is_critical flag correctly
        """
        ...
    
    def shutdown(self) -> None:
        """
        Graceful shutdown (cleanup resources).
        
        Examples:
        - ThreadPool: executor.shutdown(wait=True)
        - Ray: ray.shutdown()
        - AsyncIO: loop.close()
        """
        ...
    
    def get_metrics(self) -> dict:
        """
        Get execution metrics (optional).
        
        Returns:
            dict with metrics:
            - total_executions: int
            - failed_executions: int
            - avg_execution_time_ms: float
            - queue_depth: int (if applicable)
        """
        ...
```

---

## Strategy Implementations

### 1. SyncExecutionStrategy (Default)

**Use Case:** Simple workers, low latency, no GIL issues

```python
# backend/core/execution_strategies/sync_strategy.py

import logging
from backend.core.interfaces.execution_strategy import IExecutionStrategy
from backend.core.eventbus import CriticalEventHandlerError

logger = logging.getLogger(__name__)

class SyncExecutionStrategy:
    """
    Synchronous execution (current EventBus behavior).
    
    Pros:
    - Simple, no overhead
    - Predictable execution order
    - Easy debugging
    
    Cons:
    - Blocking (slow handler blocks EventBus)
    - No parallelism
    - Flash crash = queue backup
    """
    
    def __init__(self):
        self._metrics = {
            "total_executions": 0,
            "failed_executions": 0
        }
    
    def execute(
        self,
        handler: Callable,
        payload: BaseModel,
        subscription_id: str,
        is_critical: bool
    ) -> None:
        """Execute handler synchronously (blocking)."""
        self._metrics["total_executions"] += 1
        
        try:
            handler(payload)
        except Exception as e:
            self._metrics["failed_executions"] += 1
            
            if is_critical:
                logger.critical(
                    f"Critical handler failed: {subscription_id}",
                    exc_info=e
                )
                raise CriticalEventHandlerError(
                    f"Critical handler failed: {subscription_id}",
                    original_error=e,
                    subscription_id=subscription_id
                ) from e
            else:
                logger.error(
                    f"Handler failed: {subscription_id}",
                    exc_info=e
                )
                # Continue (no raise)
    
    def shutdown(self) -> None:
        """No resources to cleanup."""
        pass
    
    def get_metrics(self) -> dict:
        return self._metrics.copy()
```

---

### 2. ThreadPoolExecutionStrategy

**Use Case:** Flash crash protection, I/O bound workers

```python
# backend/core/execution_strategies/threadpool_strategy.py

import logging
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Dict, List
from backend.core.interfaces.execution_strategy import IExecutionStrategy

logger = logging.getLogger(__name__)

class ThreadPoolExecutionStrategy:
    """
    ThreadPoolExecutor-based async execution.
    
    Pros:
    - Non-blocking (EventBus continues accepting events)
    - Flash crash protection (queue buffering)
    - Simple (stdlib, no dependencies)
    
    Cons:
    - GIL limited (no true parallelism for CPU-bound)
    - Thread overhead (~1MB per thread)
    - Max workers limit
    
    Config:
        max_workers: int = 10
        track_futures: bool = False (memory overhead!)
    """
    
    def __init__(self, max_workers: int = 10, track_futures: bool = False):
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="EventBus-Handler-"
        )
        self._track_futures = track_futures
        self._futures: List[Future] = [] if track_futures else None
        
        self._metrics = {
            "total_executions": 0,
            "failed_executions": 0,
            "queue_depth": 0
        }
    
    def execute(
        self,
        handler: Callable,
        payload: BaseModel,
        subscription_id: str,
        is_critical: bool
    ) -> None:
        """Execute handler in thread pool (non-blocking)."""
        self._metrics["total_executions"] += 1
        
        # Submit to thread pool
        future = self._executor.submit(
            self._invoke_handler,
            handler,
            payload,
            subscription_id,
            is_critical
        )
        
        if self._track_futures:
            self._futures.append(future)
            # Cleanup completed futures
            self._futures = [f for f in self._futures if not f.done()]
            self._metrics["queue_depth"] = len(self._futures)
    
    def _invoke_handler(
        self,
        handler: Callable,
        payload: BaseModel,
        subscription_id: str,
        is_critical: bool
    ) -> None:
        """Worker thread execution (same error handling as sync)."""
        try:
            handler(payload)
        except Exception as e:
            self._metrics["failed_executions"] += 1
            
            if is_critical:
                logger.critical(
                    f"Critical handler failed: {subscription_id}",
                    exc_info=e
                )
                raise CriticalEventHandlerError(
                    f"Critical handler failed: {subscription_id}",
                    original_error=e,
                    subscription_id=subscription_id
                ) from e
            else:
                logger.error(
                    f"Handler failed: {subscription_id}",
                    exc_info=e
                )
    
    def shutdown(self) -> None:
        """Shutdown thread pool gracefully."""
        logger.info("Shutting down ThreadPoolExecutionStrategy...")
        self._executor.shutdown(wait=True)
        logger.info("ThreadPoolExecutionStrategy shutdown complete")
    
    def get_metrics(self) -> dict:
        return self._metrics.copy()
```

---

### 3. RayExecutionStrategy

**Use Case:** ML workers, CPU-intensive, distributed scaling

```python
# backend/core/execution_strategies/ray_strategy.py

import logging
import ray
from ray.actor import ActorHandle
from typing import Dict, Optional
from backend.core.interfaces.execution_strategy import IExecutionStrategy

logger = logging.getLogger(__name__)

class RayExecutionStrategy:
    """
    Ray-based distributed execution.
    
    Pros:
    - True parallelism (no GIL)
    - Distributed (multi-node scaling)
    - Fault tolerance (actor restart)
    - Efficient shared memory
    
    Cons:
    - Ray dependency (~200MB)
    - Startup overhead (~1-2s)
    - Serialization cost (pickle)
    
    Config:
        num_cpus: int = None (auto-detect)
        actors_per_handler: int = 1
        actor_options: dict = {} (Ray actor config)
    
    Architecture:
        EventBus → RayExecutionStrategy → Ray Actor Pool → Handler
    """
    
    def __init__(
        self,
        num_cpus: Optional[int] = None,
        actors_per_handler: int = 1,
        actor_options: dict = None
    ):
        # Initialize Ray (idempotent)
        if not ray.is_initialized():
            ray.init(num_cpus=num_cpus)
        
        self._actors_per_handler = actors_per_handler
        self._actor_options = actor_options or {}
        
        # Actor pool (created lazily per handler)
        self._actor_pools: Dict[str, List[ActorHandle]] = {}
        self._next_actor_index: Dict[str, int] = {}
        
        self._metrics = {
            "total_executions": 0,
            "failed_executions": 0,
            "active_actors": 0
        }
    
    def execute(
        self,
        handler: Callable,
        payload: BaseModel,
        subscription_id: str,
        is_critical: bool
    ) -> None:
        """Execute handler via Ray actor (non-blocking)."""
        self._metrics["total_executions"] += 1
        
        # Get or create actor pool for this handler
        actor = self._get_or_create_actor(handler, subscription_id)
        
        # Fire Ray task (non-blocking!)
        try:
            # Serialize payload
            payload_dict = payload.dict()
            
            # Submit remote task
            future = actor.execute_handler.remote(
                payload_dict,
                subscription_id,
                is_critical
            )
            
            # Optional: Track future for result/error handling
            # (For now: fire and forget)
            
        except Exception as e:
            self._metrics["failed_executions"] += 1
            logger.error(
                f"Failed to submit Ray task for {subscription_id}",
                exc_info=e
            )
    
    def _get_or_create_actor(
        self,
        handler: Callable,
        subscription_id: str
    ) -> ActorHandle:
        """
        Get existing actor or create new one.
        
        Load balancing: Round-robin across actor pool.
        """
        handler_key = f"{handler.__module__}.{handler.__name__}"
        
        # Create actor pool if not exists
        if handler_key not in self._actor_pools:
            self._actor_pools[handler_key] = [
                self._create_actor(handler)
                for _ in range(self._actors_per_handler)
            ]
            self._next_actor_index[handler_key] = 0
            self._metrics["active_actors"] += self._actors_per_handler
        
        # Round-robin selection
        pool = self._actor_pools[handler_key]
        index = self._next_actor_index[handler_key]
        self._next_actor_index[handler_key] = (index + 1) % len(pool)
        
        return pool[index]
    
    def _create_actor(self, handler: Callable) -> ActorHandle:
        """Create Ray actor for handler."""
        
        # Define Ray actor class dynamically
        @ray.remote
        class HandlerActor:
            def __init__(self, handler_fn):
                self.handler = handler_fn
            
            def execute_handler(
                self,
                payload_dict: dict,
                subscription_id: str,
                is_critical: bool
            ):
                # Reconstruct payload (assumes DTO available in actor)
                # TODO: Pass DTO class for proper reconstruction
                
                try:
                    self.handler(payload_dict)
                except Exception as e:
                    if is_critical:
                        # TODO: Propagate to main process
                        raise
                    else:
                        logger.error(f"Handler failed: {subscription_id}")
        
        # Create actor with options
        actor = HandlerActor.remote(handler)
        return actor
    
    def shutdown(self) -> None:
        """Shutdown Ray actors."""
        logger.info("Shutting down RayExecutionStrategy...")
        
        # Kill all actors
        for pool in self._actor_pools.values():
            for actor in pool:
                ray.kill(actor)
        
        self._actor_pools.clear()
        self._metrics["active_actors"] = 0
        
        logger.info("RayExecutionStrategy shutdown complete")
    
    def get_metrics(self) -> dict:
        return self._metrics.copy()
```

---

## EventBus Integration

### Updated EventBus Implementation

```python
# backend/core/eventbus.py (ENHANCED)

from backend.core.interfaces.execution_strategy import IExecutionStrategy
from backend.core.execution_strategies.sync_strategy import SyncExecutionStrategy

class EventBus(IEventBus):
    """
    Thread-safe platform-wide event bus with pluggable execution.
    
    Execution strategy is injected via __init__ (DI pattern).
    """
    
    def __init__(self, execution_strategy: IExecutionStrategy = None):
        """
        Initialize EventBus with execution strategy.
        
        Args:
            execution_strategy: Handler execution backend
                Default: SyncExecutionStrategy (backward compatible)
        """
        self._subscriptions: Dict[str, List[Subscription]] = {}
        self._subscription_index: Dict[str, Subscription] = {}
        self._lock = threading.RLock()
        
        # 🔥 PLUGGABLE EXECUTION STRATEGY
        self._execution_strategy = execution_strategy or SyncExecutionStrategy()
    
    def _invoke_handler(
        self,
        subscription: Subscription,
        payload: BaseModel
    ) -> None:
        """
        Invoke handler via execution strategy.
        
        EventBus does NOT know how handler is executed.
        Strategy handles sync/async/distributed execution.
        """
        self._execution_strategy.execute(
            handler=subscription.handler,
            payload=payload,
            subscription_id=subscription.subscription_id,
            is_critical=subscription.is_critical
        )
    
    def shutdown(self) -> None:
        """Shutdown EventBus and execution strategy."""
        logger.info("Shutting down EventBus...")
        self._execution_strategy.shutdown()
        logger.info("EventBus shutdown complete")
```

---

## Configuration System

### Platform Config Schema

```yaml
# platform_config.yaml

execution:
  # Strategy selection (ZERO EFFORT SWITCH!)
  strategy: "threadpool"  # "sync" | "threadpool" | "ray" | "asyncio"
  
  # Strategy-specific config
  sync:
    # No config needed
  
  threadpool:
    max_workers: 10
    track_futures: false
  
  ray:
    num_cpus: 8  # null = auto-detect
    actors_per_handler: 2
    actor_options:
      num_cpus: 1
      memory: 1073741824  # 1GB
  
  asyncio:
    # TODO: AsyncIO strategy config
```

### ExecutionStrategyFactory

```python
# backend/assembly/factories/execution_strategy_factory.py

from typing import Optional
from backend.core.interfaces.execution_strategy import IExecutionStrategy
from backend.core.execution_strategies.sync_strategy import SyncExecutionStrategy
from backend.core.execution_strategies.threadpool_strategy import ThreadPoolExecutionStrategy
from backend.core.execution_strategies.ray_strategy import RayExecutionStrategy

class ExecutionStrategyFactory:
    """
    Factory for creating execution strategies from config.
    
    Single source of truth for strategy creation.
    """
    
    @staticmethod
    def create_from_config(config: dict) -> IExecutionStrategy:
        """
        Create execution strategy from platform config.
        
        Args:
            config: execution section from platform_config.yaml
        
        Returns:
            IExecutionStrategy implementation
        
        Raises:
            ValueError: If unknown strategy type
        """
        strategy_type = config.get("strategy", "sync")
        
        if strategy_type == "sync":
            return SyncExecutionStrategy()
        
        elif strategy_type == "threadpool":
            threadpool_config = config.get("threadpool", {})
            return ThreadPoolExecutionStrategy(
                max_workers=threadpool_config.get("max_workers", 10),
                track_futures=threadpool_config.get("track_futures", False)
            )
        
        elif strategy_type == "ray":
            ray_config = config.get("ray", {})
            return RayExecutionStrategy(
                num_cpus=ray_config.get("num_cpus"),
                actors_per_handler=ray_config.get("actors_per_handler", 1),
                actor_options=ray_config.get("actor_options", {})
            )
        
        else:
            raise ValueError(f"Unknown execution strategy: {strategy_type}")
```

### Bootstrap Integration

```python
# backend/assembly/bootstrap.py

class PlatformBootstrap:
    """Bootstrap platform components from config."""
    
    def bootstrap_platform(self, platform_config: dict) -> Platform:
        """
        Bootstrap platform with execution strategy.
        
        Strategy is created ONCE at platform startup.
        All strategies share same EventBus instance.
        """
        # Create execution strategy from config
        execution_config = platform_config.get("execution", {})
        execution_strategy = ExecutionStrategyFactory.create_from_config(
            execution_config
        )
        
        # Create EventBus with strategy (DI)
        event_bus = EventBus(execution_strategy=execution_strategy)
        
        # ... rest of platform bootstrap ...
        
        return Platform(
            event_bus=event_bus,
            execution_strategy=execution_strategy  # For metrics/shutdown
        )
```

---

## Per-Worker Strategy Override (Future)

### Worker Manifest (Optional Strategy)

```yaml
# plugins/signal_detectors/ml_momentum/manifest.yaml
plugin_id: "s1mple/ml_momentum/v1.0.0"

execution:
  # Override platform execution strategy for THIS worker
  strategy: "ray"
  config:
    actors_per_handler: 4  # Heavy ML = more actors
```

### Subscription With Strategy Override

```python
class Subscription:
    subscription_id: str
    event_name: str
    handler: Callable
    scope: SubscriptionScope
    is_critical: bool
    execution_strategy: Optional[IExecutionStrategy] = None  # 🔥 Per-worker override!

class EventBus:
    def _invoke_handler(self, subscription, payload):
        # Use worker-specific strategy if available
        strategy = subscription.execution_strategy or self._execution_strategy
        
        strategy.execute(
            handler=subscription.handler,
            payload=payload,
            subscription_id=subscription.subscription_id,
            is_critical=subscription.is_critical
        )
```

---

## Testing Strategy

### Unit Tests (Strategy Implementations)

```python
# tests/unit/core/execution_strategies/test_sync_strategy.py

class TestSyncExecutionStrategy:
    def test_execute_handler_success(self):
        """Test successful handler execution."""
        strategy = SyncExecutionStrategy()
        
        handler = Mock()
        payload = Mock(spec=BaseModel)
        
        strategy.execute(handler, payload, "SUB_123", is_critical=False)
        
        handler.assert_called_once_with(payload)
    
    def test_execute_critical_handler_failure_raises(self):
        """Test critical handler failure raises exception."""
        strategy = SyncExecutionStrategy()
        
        handler = Mock(side_effect=ValueError("Test error"))
        payload = Mock(spec=BaseModel)
        
        with pytest.raises(CriticalEventHandlerError):
            strategy.execute(handler, payload, "SUB_123", is_critical=True)
    
    def test_execute_non_critical_handler_failure_logs(self):
        """Test non-critical handler failure logs error."""
        strategy = SyncExecutionStrategy()
        
        handler = Mock(side_effect=ValueError("Test error"))
        payload = Mock(spec=BaseModel)
        
        # Should not raise
        strategy.execute(handler, payload, "SUB_123", is_critical=False)
        
        # Verify metrics
        assert strategy.get_metrics()["failed_executions"] == 1
```

### Integration Tests (EventBus + Strategy)

```python
# tests/integration/test_eventbus_execution_strategies.py

class TestEventBusWithStrategies:
    """Test EventBus with different execution strategies."""
    
    @pytest.mark.parametrize("strategy", [
        SyncExecutionStrategy(),
        ThreadPoolExecutionStrategy(max_workers=2),
        # RayExecutionStrategy()  # Requires Ray
    ])
    def test_eventbus_with_strategy(self, strategy):
        """Test EventBus works with any strategy."""
        bus = EventBus(execution_strategy=strategy)
        
        handler = Mock()
        scope = SubscriptionScope(
            level=ScopeLevel.PLATFORM,
            strategy_instance_id=None
        )
        
        sub_id = bus.subscribe("TEST", handler, scope)
        
        payload = Mock(spec=BaseModel)
        bus.publish("TEST", payload, ScopeLevel.PLATFORM)
        
        # Give async strategies time to execute
        if isinstance(strategy, ThreadPoolExecutionStrategy):
            time.sleep(0.1)
        
        handler.assert_called_once()
        
        bus.shutdown()
```

### Performance Benchmarks

```python
# tests/benchmarks/test_execution_strategy_performance.py

class TestExecutionStrategyPerformance:
    """Benchmark different execution strategies."""
    
    def test_throughput_comparison(self):
        """Compare throughput of strategies."""
        
        # Setup
        num_events = 1000
        handler_delay_ms = 10
        
        def slow_handler(payload):
            time.sleep(handler_delay_ms / 1000)
        
        strategies = {
            "sync": SyncExecutionStrategy(),
            "threadpool_10": ThreadPoolExecutionStrategy(max_workers=10),
            # "ray_4": RayExecutionStrategy(actors_per_handler=4)
        }
        
        results = {}
        
        for name, strategy in strategies.items():
            bus = EventBus(execution_strategy=strategy)
            scope = SubscriptionScope(ScopeLevel.PLATFORM, None)
            bus.subscribe("PERF_TEST", slow_handler, scope)
            
            start = time.time()
            
            for i in range(num_events):
                bus.publish("PERF_TEST", Mock(spec=BaseModel), ScopeLevel.PLATFORM)
            
            # Wait for completion
            if isinstance(strategy, ThreadPoolExecutionStrategy):
                time.sleep(2)  # Give threads time to finish
            
            elapsed = time.time() - start
            throughput = num_events / elapsed
            
            results[name] = {
                "elapsed_seconds": elapsed,
                "throughput_events_per_second": throughput
            }
            
            bus.shutdown()
        
        # Print results
        print("\n=== Execution Strategy Performance ===")
        for name, metrics in results.items():
            print(f"{name}:")
            print(f"  Elapsed: {metrics['elapsed_seconds']:.2f}s")
            print(f"  Throughput: {metrics['throughput_events_per_second']:.2f} events/s")
```

---

## Migration Path

### Phase 1: Protocol + SyncStrategy (Week 1)
- ✅ Define IExecutionStrategy protocol
- ✅ Implement SyncExecutionStrategy (current behavior)
- ✅ Update EventBus to use strategy (DI)
- ✅ Add ExecutionStrategyFactory
- ✅ Update bootstrap
- ✅ Backward compatible (default = sync)

### Phase 2: ThreadPoolStrategy (Week 2)
- ✅ Implement ThreadPoolExecutionStrategy
- ✅ Add config support
- ✅ Test flash crash scenario
- ✅ Production rollout (config change only!)

### Phase 3: RayStrategy (Week 3-4)
- ✅ Implement RayExecutionStrategy
- ✅ Actor pool management
- ✅ Serialization handling
- ✅ Test ML worker scenario
- ✅ Optional: Per-worker strategy override

### Phase 4: Monitoring & Optimization (Ongoing)
- ✅ Metrics dashboard
- ✅ Performance tuning
- ✅ Auto-scaling (Ray)

---

## Zero-Effort Switch Demo

### Before (Production - Sync)
```yaml
# platform_config.yaml
execution:
  strategy: "sync"
```

### After (Production - ThreadPool for Flash Crash)
```yaml
# platform_config.yaml
execution:
  strategy: "threadpool"
  threadpool:
    max_workers: 20
```

**Actions Required:**
1. Edit YAML (1 line change)
2. Restart platform

**Code Changes:** ZERO ✅

---

## Architecture Benefits

### Single Responsibility
- **EventBus**: Event routing (scope, subscriptions)
- **ExecutionStrategy**: Handler execution (sync/async/distributed)
- **Factory**: Strategy creation from config

### Open/Closed Principle
- **Open**: Add new strategies (AsyncIO, Celery, etc.)
- **Closed**: EventBus code unchanged

### Dependency Inversion
- **EventBus depends on IExecutionStrategy** (abstraction)
- **Concrete strategies injected** (DI)

### Configuration-Driven
- **Behavior controlled by YAML** (not code)
- **Zero-effort switching** (change config, restart)

### Testable
- **Mock ExecutionStrategy** for unit tests
- **Benchmark strategies** easily

---

## See Also

- [EventBus Design](EVENT_LIFECYCLE_ARCHITECTURE.md)
- [Platform Components](../architecture/PLATFORM_COMPONENTS.md)
- [Configuration Architecture](CONFIG_SCHEMA_ARCHITECTURE.md)

---

**Last Updated:** 2025-11-05  
**Document Status:** Design  
**Implementation Status:** Not Started
