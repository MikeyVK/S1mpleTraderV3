# EventBus Design - Platform-Wide Event System

**Status:** Design Approved  
**Implementation Phase:** Phase 1.2 (Core Protocols)  
**Created:** 2025-10-29  
**TDD Branch:** `feature/eventbus-protocol`

## Overview

EventBus is a **thread-safe, platform-wide singleton** that enables N-to-N event communication between strategies and platform services. It supports flexible scoping, critical error handling, and selective listening for performance optimization.

## Core Principles

### 1. Platform Singleton (Not Per-Strategy)

- **One EventBus instance** shared across all StrategieInstanties
- Initialized once by OperationService
- Enables cross-strategy communication via platform services
- Supports system-wide events (e.g., PORTFOLIO_RISK_HIGH)

### 2. Bus-Agnostic Workers

Workers **never** call EventBus directly:

```python
# ❌ WRONG - Worker depends on EventBus
class MyWorker:
    def __init__(self, event_bus: IEventBus):
        self._event_bus = event_bus
    
    def process(self):
        self._event_bus.publish("EVENT", payload)

# ✅ CORRECT - Worker returns DispositionEnvelope
class MyWorker:
    def process(self) -> DispositionEnvelope:
        return DispositionEnvelope(
            disposition="PUBLISH",
            event_payload=OpportunitySignal(...)
        )
```

**EventAdapter** bridges worker and bus:

```python
class EventAdapter:
    def _on_event(self, event):
        envelope = self._worker.process()
        
        if envelope.disposition == "PUBLISH":
            self._event_bus.publish(
                event_name=envelope.event_name or self._default_event,
                payload=envelope.event_payload,
                scope=ScopeLevel.STRATEGY,
                strategy_instance_id=self._strategy_id
            )
```

### 3. Dumb Message Broker

EventBus is **intentionally simple**:

- ✅ Knows: Event names, handlers, scopes, criticality
- ❌ Doesn't know: Workers, Operators, Adapters, business logic

**Smart orchestration** happens in EventWiringFactory.

## Architecture Components

### SubscriptionScope - Flexible Event Filtering

```python
from dataclasses import dataclass
from typing import Set, Optional
from enum import Enum

class ScopeLevel(Enum):
    """Base scope level."""
    PLATFORM = "platform"  # Platform-wide visibility
    STRATEGY = "strategy"  # Strategy-isolated

@dataclass(frozen=True)
class SubscriptionScope:
    """
    Defines what events a subscription should receive.
    
    Filtering Rules:
    1. STRATEGY subscription:
       - Receives: Own strategy events + platform events
       - Filters out: Other strategy events
    
    2. PLATFORM subscription (unrestricted):
       - target_strategy_ids=None
       - Receives: ALL events (all strategies + platform)
    
    3. PLATFORM subscription (selective):
       - target_strategy_ids={specific strategies}
       - Receives: Specified strategy events + platform events
       - Filters out: Other strategy events
    """
    level: ScopeLevel
    strategy_instance_id: Optional[str] = None  # Required for STRATEGY level
    target_strategy_ids: Optional[Set[str]] = None  # Optional filter for PLATFORM
    
    def should_receive_event(
        self,
        publish_scope: ScopeLevel,
        publish_strategy_id: Optional[str]
    ) -> bool:
        """
        Determine if subscription should receive event.
        
        Args:
            publish_scope: Scope of published event
            publish_strategy_id: Strategy that published (None for platform)
        
        Returns:
            True if subscription should receive event
        """
        # Platform-scoped events → everyone receives
        if publish_scope == ScopeLevel.PLATFORM:
            return True
        
        # Strategy-scoped events
        if self.level == ScopeLevel.STRATEGY:
            # Only receive own strategy events
            return self.strategy_instance_id == publish_strategy_id
        
        if self.level == ScopeLevel.PLATFORM:
            # Unrestricted → receive all
            if self.target_strategy_ids is None:
                return True
            
            # Selective → only matching strategies
            return publish_strategy_id in self.target_strategy_ids
        
        return False
```

### IEventBus Protocol

```python
from typing import Protocol, Callable
from pydantic import BaseModel

class IEventBus(Protocol):
    """
    Thread-safe platform-wide event bus.
    
    Responsibilities:
    - Event publishing with scope filtering
    - Subscription management with flexible scoping
    - Critical error handling (crash vs log)
    - Thread-safe concurrent access
    
    Non-Responsibilities:
    - Business logic understanding
    - Component type knowledge
    - Wiring decisions
    """
    
    def publish(
        self,
        event_name: str,
        payload: BaseModel,
        scope: ScopeLevel,
        strategy_instance_id: Optional[str] = None
    ) -> None:
        """
        Broadcast event to matching subscribers.
        
        Args:
            event_name: Event identifier (e.g., "OPPORTUNITY_DETECTED")
            payload: Pydantic DTO (validated contract)
            scope: PLATFORM (all) or STRATEGY (scoped)
            strategy_instance_id: Required if scope=STRATEGY
        
        Raises:
            CriticalEventHandlerError: If is_critical handler fails
        
        Thread-Safety:
            Multiple threads can publish concurrently
        """
        ...
    
    def subscribe(
        self,
        event_name: str,
        handler: Callable[[BaseModel], None],
        scope: SubscriptionScope,
        is_critical: bool = False
    ) -> str:
        """
        Register event handler with flexible scoping.
        
        Args:
            event_name: Event to listen for
            handler: Callback function (receives payload)
            scope: Defines filtering behavior:
                - STRATEGY: Own events + platform events
                - PLATFORM (unrestricted): All events
                - PLATFORM (selective): Specific strategies + platform
            is_critical: Error handling mode:
                - True: Handler failure crashes everything
                - False: Handler failure logged, continues
        
        Returns:
            subscription_id: Unique ID for unsubscribe
        
        Thread-Safety:
            Can subscribe while events are being published
        """
        ...
    
    def unsubscribe(self, subscription_id: str) -> None:
        """
        Remove subscription.
        
        Args:
            subscription_id: ID returned from subscribe()
        
        Thread-Safety:
            Can unsubscribe while events are being published
        """
        ...
```

## Implementation Details

### Thread Safety Strategy

**RLock (Reentrant Lock)** for all shared state access:

```python
import threading

class EventBus:
    def __init__(self):
        self._subscriptions: Dict[str, List[Subscription]] = {}
        self._lock = threading.RLock()  # Reentrant lock
    
    def publish(self, event_name, payload, scope, strategy_id):
        # Lock ONLY for reading subscription list
        with self._lock:
            matching_subscriptions = [
                sub for sub in self._subscriptions.get(event_name, [])
                if sub.scope.should_receive_event(scope, strategy_id)
            ]
        
        # Release lock BEFORE invoking handlers (avoid deadlocks)
        for subscription in matching_subscriptions:
            self._invoke_handler(subscription, payload)
```

**Why RLock:**
- Allows same thread to acquire multiple times
- Prevents deadlocks in complex event chains
- Safer than basic Lock for nested calls

### Error Handling Strategy

**Scope-Dependent Error Propagation:**

```python
def _invoke_handler(self, subscription: Subscription, payload: BaseModel):
    """
    Invoke handler with scope-aware error handling.
    
    Rules:
    - is_critical=True (singleton): Crash everything
    - is_critical=False (strategy): Log + continue
    """
    try:
        subscription.handler(payload)
    except Exception as e:
        if subscription.is_critical:
            # Platform singleton failure = STOP EVERYTHING
            raise CriticalEventHandlerError(
                f"Critical handler failed for event {subscription.event_name}",
                original_error=e,
                subscription_id=subscription.subscription_id
            ) from e
        else:
            # Strategy worker failure = LOG + CONTINUE
            logger.error(
                f"Handler failed for strategy {subscription.scope.strategy_instance_id}",
                exc_info=e,
                extra={
                    "event_name": subscription.event_name,
                    "subscription_id": subscription.subscription_id
                }
            )
```

### Performance Optimization

**Selective Platform Listening** reduces irrelevant handler calls:

```python
# Scenario: 10 strategies, 5 platform singletons

# Event: TICK from STR_A

# Without filtering (old):
# - All 10 strategy workers invoked (9 irrelevant)
# - All 5 singletons invoked (maybe irrelevant)
# = 15 calls

# With selective filtering (new):
# - STR_A worker (scope matches)
# - AggregatedLedger (target_strategy_ids=None → all)
# - DebugMonitor (target_strategy_ids={STR_A} → matches)
# - ComplianceValidator (target_strategy_ids=None → all)
# = 4 calls (73% reduction!)
```

## Usage Examples

### Example 1: Strategy Worker (Most Restrictive)

```python
# EventWiringFactory creates subscription for strategy worker
event_bus.subscribe(
    event_name="TICK",
    handler=worker.on_tick,
    scope=SubscriptionScope(
        level=ScopeLevel.STRATEGY,
        strategy_instance_id="STR_A"
    ),
    is_critical=False  # Strategy failure = log + continue
)

# Receives:
# ✅ TICK events from STR_A
# ✅ Platform events (e.g., PORTFOLIO_RISK_HIGH)
# ❌ TICK events from STR_B, STR_C, etc.
```

### Example 2: AggregatedLedger (Unrestricted Platform)

```python
# Platform singleton that needs ALL strategy updates
event_bus.subscribe(
    event_name="LEDGER_STATE_CHANGED",
    handler=aggregated_ledger.on_ledger_update,
    scope=SubscriptionScope(
        level=ScopeLevel.PLATFORM,
        target_strategy_ids=None  # ← Unrestricted!
    ),
    is_critical=True  # Ledger failure = crash everything
)

# Receives:
# ✅ LEDGER_STATE_CHANGED from ALL strategies
# ✅ Platform events
```

### Example 3: Debug Monitor (Selective Platform)

```python
# Platform service monitoring specific strategies only
event_bus.subscribe(
    event_name="OPPORTUNITY_DETECTED",
    handler=debug_monitor.log_opportunity,
    scope=SubscriptionScope(
        level=ScopeLevel.PLATFORM,
        target_strategy_ids={"STR_A", "STR_C"}  # ← Selective!
    ),
    is_critical=False  # Debug failure = just log
)

# Receives:
# ✅ OPPORTUNITY_DETECTED from STR_A
# ✅ OPPORTUNITY_DETECTED from STR_C
# ✅ Platform events
# ❌ OPPORTUNITY_DETECTED from STR_B, STR_D, etc.
```

### Example 4: Cross-Strategy Communication (Via Singleton)

```python
# ThreatWorker in Strategy A listens to platform-wide risk event
event_bus.subscribe(
    event_name="PORTFOLIO_RISK_HIGH",  # Published by AggregatedLedger
    handler=threat_worker.on_portfolio_risk,
    scope=SubscriptionScope(
        level=ScopeLevel.PLATFORM,  # ← Listen to platform events
        strategy_instance_id="STR_A"  # ← But still within STR_A context
    ),
    is_critical=False
)

# Architecture:
# STR_B triggers risk → AggregatedLedger detects → publishes PORTFOLIO_RISK_HIGH
# → All strategy ThreatWorkers receive event → can react within own strategy
```

**Note:** NO direct cross-strategy listening! Always via platform singleton intermediary.

## Bootstrap Integration

### OperationService Initialization

```python
class OperationService:
    def __init__(self):
        # Initialize singletons
        self.event_bus = EventBus()  # ← Platform singleton
        self.aggregated_ledger = AggregatedLedger()
        self.scheduler = Scheduler()
        
        # Wire platform singletons
        self._wire_platform_singletons()
    
    def _wire_platform_singletons(self):
        """Wire platform services to EventBus."""
        # AggregatedLedger listens to all strategy ledgers
        self.event_bus.subscribe(
            event_name="LEDGER_STATE_CHANGED",
            handler=self.aggregated_ledger.on_ledger_update,
            scope=SubscriptionScope(
                level=ScopeLevel.PLATFORM,
                target_strategy_ids=None
            ),
            is_critical=True
        )
```

### Strategy Instance Wiring

```python
def start_strategy(self, strategy_link) -> str:
    # ... load config, translate to BuildSpecs ...
    
    # D: Bedraad het Systeem
    event_wiring_factory.wire_all_from_spec(
        wiring_spec=build_specs.wiring_spec,
        operator_map=operator_map,
        worker_instances=worker_instances,
        event_bus=self.event_bus,  # ← Shared singleton
        strategy_instance_id=strategy_instance_id
    )
```

### EventWiringFactory Logic

```python
class EventWiringFactory:
    def wire_all_from_spec(
        self,
        wiring_spec: WiringSpec,
        operator_map: Dict,
        worker_instances: Dict,
        event_bus: IEventBus,
        strategy_instance_id: str
    ):
        for wiring in wiring_spec.event_wirings:
            component = self._resolve_component(wiring.subscriber_id, ...)
            
            # Determine scope and criticality
            scope = SubscriptionScope(
                level=ScopeLevel.STRATEGY,
                strategy_instance_id=strategy_instance_id
            )
            is_critical = False  # Strategy workers not critical
            
            # EventBus stays dumb - just receives the configuration
            event_bus.subscribe(
                event_name=wiring.event_name,
                handler=component.handler_method,
                scope=scope,
                is_critical=is_critical
            )
```

## Test Strategy

### Unit Tests (20+ Tests)

**Protocol Tests** (`tests/unit/core/interfaces/test_eventbus.py`):
- Subscription creation and ID generation
- Unsubscribe functionality
- SubscriptionScope filtering logic
- Multiple subscriptions to same event
- No subscriptions for event

**Implementation Tests** (`tests/unit/core/test_eventbus.py`):
- Basic publish/subscribe flow
- STRATEGY scope filtering (only own events)
- PLATFORM scope unrestricted (receives all)
- PLATFORM scope selective (target_strategy_ids)
- Platform event broadcast (all receive)
- Critical error handling (crash)
- Non-critical error handling (log + continue)
- Thread safety (concurrent publish/subscribe)
- Thread safety (concurrent unsubscribe)
- Multiple handlers for same event
- Handler receives correct payload
- Subscription ID uniqueness
- Unsubscribe removes handler
- Invalid subscription ID handling

### Integration Tests

- End-to-end: Worker → EventAdapter → EventBus → Handler
- Multi-strategy scenario (3 strategies, shared bus)
- Platform singleton communication (AggregatedLedger)
- Cross-strategy via platform (PORTFOLIO_RISK_HIGH)

## Quality Gates

**Target:**
- ✅ Pylint: 10.00/10 (all gates)
- ✅ Tests: 100% passing (20+ tests)
- ✅ Line length: <100 chars
- ✅ Imports: Top-level only
- ✅ Docstrings: Complete coverage

## Migration Path

**Current State:**
- EventBus concept exists in docs
- No implementation

**Phase 1.2 Implementation:**
1. ✅ IEventBus protocol definition
2. ✅ SubscriptionScope helper class
3. ✅ EventBus singleton implementation
4. ✅ Thread safety (RLock)
5. ✅ Test coverage (20+ tests)

**Phase 3.2 Integration:**
- EventWiringFactory implementation
- OperationService integration
- Platform singleton wiring
- Strategy instance wiring

## Related Documentation

- **Architecture:** [ARCHITECTURAL_SHIFTS.md](../architecture/ARCHITECTURAL_SHIFTS.md) - Platgeslagen Orkestratie
- **Config:** [Addendum 3.8](../system/addendums/Addendum_3.8_Configuratie_en_Vertaal_Filosofie.md) - OperationService orchestration
- **Point-in-Time Model:** [POINT_IN_TIME_MODEL.md](../architecture/POINT_IN_TIME_MODEL.md) - Two communication paths
- **Implementation Status:** [IMPLEMENTATION_STATUS.md](../implementation/IMPLEMENTATION_STATUS.md) - Phase tracking

## Decision Log

**2025-10-29: Thread Safety from Day 1**
- Decision: Implement RLock from beginning (not later)
- Rationale: Avoid refactor pain, prepare for live trading

**2025-10-29: Selective Platform Listening**
- Decision: Add `target_strategy_ids` filter for PLATFORM subscriptions
- Rationale: 73% performance improvement, enables debugging/monitoring use cases
- Trade-off: Slightly more complex, but worth the flexibility

**2025-10-29: Explicit is_critical Flag**
- Decision: EventWiringFactory determines criticality, EventBus receives flag
- Rationale: SRP - EventBus stays dumb, factory stays smart
- Rejected: Automatic derivation from scope (violates SRP)
