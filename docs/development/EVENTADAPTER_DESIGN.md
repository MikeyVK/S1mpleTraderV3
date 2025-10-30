# EventAdapter Design - Worker-EventBus Bridge

**Status:** Design Approved  
**Implementation Phase:** Phase 2.1 (Assembly Layer)  
**Created:** 2025-10-30  
**Priority:** HIGH - Critical Path Component

---

## Overview

EventAdapter is the **glue component** between workers and EventBus, enabling event-driven worker orchestration without coupling workers to the EventBus infrastructure. Each worker/component gets its own EventAdapter instance (1-to-1 relationship).

### Core Principles

1. **Bus-Agnostic Workers**: Workers never import or depend on EventBus
2. **DispositionEnvelope Interpretation**: Adapter translates worker intent to bus actions
3. **Flexible Wiring**: Configuration-driven event routing via `wiring_map.yaml`
4. **System Event Generation**: Auto-generates UUID-based event names for flow tracking

---

## Architecture Context

### Platgeslagen Orkestratie (Flattened Orchestration)

V3 removes V2's Operator layer and uses direct event-driven wiring:

```mermaid
graph LR
    W1[Worker 1] -->|DispositionEnvelope| A1[EventAdapter 1]
    W2[Worker 2] -->|DispositionEnvelope| A2[EventAdapter 2]
    W3[Worker 3] -->|DispositionEnvelope| A3[EventAdapter 3]
    
    A1 -->|publish events| Bus[EventBus]
    A2 -->|publish events| Bus
    A3 -->|publish events| Bus
    
    Bus -->|notify subscribers| A1
    Bus -->|notify subscribers| A2
    Bus -->|notify subscribers| A3
    
    A1 -->|trigger| W1
    A2 -->|trigger| W2
    A3 -->|trigger| W3
    
    style Bus fill:#e1f5ff
    style A1 fill:#fff4e1
    style A2 fill:#fff4e1
    style A3 fill:#fff4e1
```

**Key Relationships:**
- EventAdapter ↔ Worker: 1-to-1 (each worker has dedicated adapter)
- EventAdapter ↔ EventBus: N-to-1 (all adapters share platform singleton)
- EventBus ↔ EventAdapter: N-to-N (pub/sub pattern)

---

## Responsibilities

### 1. Event Subscription Management

Subscribe to events specified in wiring configuration:

```python
# EventAdapter subscribes to events on behalf of worker
subscriptions = [
    "_tick_flow_start_abc123",      # System event from TickCacheManager
    "_ema_detector_output_def456",  # System event from previous worker
    "EMERGENCY_HALT"                # Custom event from threat worker
]

for event_name in subscriptions:
    subscription_id = event_bus.subscribe(
        event_name=event_name,
        handler=self._on_event_received,
        scope="STRATEGY",
        strategy_id=strategy_id
    )
```

### 2. Worker Invocation

Trigger worker when subscribed event is published:

```python
def _on_event_received(self, event_name: str, payload: BaseModel | None) -> None:
    """Handle event notification from EventBus."""
    # 1. Map event to handler method (from wiring config)
    handler_method = self._handler_mapping[event_name]  # e.g., "process"
    
    # 2. Invoke worker method
    method = getattr(self._worker, handler_method)
    envelope = method(payload)  # Returns DispositionEnvelope
    
    # 3. Interpret disposition
    self._handle_disposition(envelope, event_name)
```

### 3. DispositionEnvelope Interpretation

Process worker's return value and execute appropriate action:

```python
def _handle_disposition(
    self, 
    envelope: DispositionEnvelope, 
    triggering_event: str
) -> None:
    """Execute action based on worker's disposition."""
    
    if envelope.disposition == "CONTINUE":
        # Publish system event for flow continuation
        system_event_name = self._generate_system_event_name()
        self._event_bus.publish(
            event_name=system_event_name,
            payload=None,  # Data in TickCache, not event payload
            scope="STRATEGY",
            strategy_id=self._strategy_id
        )
    
    elif envelope.disposition == "PUBLISH":
        # Publish custom event with optional payload
        self._validate_custom_event(envelope.event_name)
        self._event_bus.publish(
            event_name=envelope.event_name,
            payload=envelope.event_payload,
            scope="STRATEGY",
            strategy_id=self._strategy_id
        )
    
    elif envelope.disposition == "STOP":
        # Publish flow-stop event for cleanup
        stop_event_name = self._generate_stop_event_name()
        self._event_bus.publish(
            event_name=stop_event_name,
            payload=None,
            scope="STRATEGY",
            strategy_id=self._strategy_id
        )
```

### 4. System Event Generation

Auto-generate unique event names for internal flow tracking:

```python
def _generate_system_event_name(self) -> str:
    """Generate UUID-based system event name.
    
    Format: _{component_id}_output_{uuid}
    Example: _ema_detector_instance_1_output_a1b2c3d4
    """
    unique_id = str(uuid4())[:8]
    return f"_{self._component_id}_output_{unique_id}"

def _generate_stop_event_name(self) -> str:
    """Generate flow-stop event name.
    
    Format: _{strategy_id}_flow_stop_{uuid}
    Example: _btc_momentum_flow_stop_xyz789
    """
    unique_id = str(uuid4())[:8]
    return f"_{self._strategy_id}_flow_stop_{unique_id}"
```

### 5. Custom Event Validation

Ensure workers only publish events declared in their manifest:

```python
def _validate_custom_event(self, event_name: str) -> None:
    """Validate worker is allowed to publish this custom event.
    
    Raises:
        ValueError: If event_name not in manifest's publishes list
    """
    if event_name not in self._allowed_publications:
        raise ValueError(
            f"Worker '{self._component_id}' attempted to publish "
            f"undeclared event '{event_name}'. "
            f"Allowed events: {self._allowed_publications}"
        )
```

---

## Class Design

### EventAdapter

**Location:** `backend/assembly/event_adapter.py`

```python
from uuid import uuid4
from typing import Dict, Set, Callable, Any
from pydantic import BaseModel

from backend.core.interfaces.eventbus import IEventBus
from backend.core.interfaces.worker import IWorker
from backend.dtos.shared.disposition_envelope import DispositionEnvelope


class EventAdapter:
    """
    Bridge between worker and EventBus.
    
    Enables event-driven worker orchestration while keeping workers
    bus-agnostic. Each worker gets its own adapter instance.
    
    Responsibilities:
        - Subscribe to events on behalf of worker
        - Invoke worker when events are received
        - Interpret DispositionEnvelope and execute actions
        - Generate system events for flow tracking
        - Validate custom event publications
    
    Architecture:
        Worker ←→ EventAdapter (1-to-1)
        EventAdapter ←→ EventBus (N-to-1)
        EventBus ←→ EventAdapter (N-to-N pub/sub)
    """
    
    def __init__(
        self,
        component_id: str,
        worker: IWorker,
        event_bus: IEventBus,
        strategy_id: str,
        subscriptions: list[str],
        handler_mapping: Dict[str, str],
        allowed_publications: Set[str]
    ):
        """
        Initialize EventAdapter.
        
        Args:
            component_id: Unique identifier for this worker instance
                (e.g., "ema_detector_instance_1")
            worker: Worker instance to adapt
            event_bus: Platform EventBus singleton
            strategy_id: Strategy this worker belongs to
            subscriptions: Event names to subscribe to
                (e.g., ["_tick_flow_start_abc", "_ema_output_def"])
            handler_mapping: Maps event_name → worker method name
                (e.g., {"_tick_flow_start_abc": "process"})
            allowed_publications: Custom events worker may publish
                (from manifest publishes list)
        """
        self._component_id = component_id
        self._worker = worker
        self._event_bus = event_bus
        self._strategy_id = strategy_id
        self._subscriptions = subscriptions
        self._handler_mapping = handler_mapping
        self._allowed_publications = allowed_publications
        
        # Track subscription IDs for cleanup
        self._subscription_ids: list[str] = []
        
        # Subscribe to all configured events
        self._subscribe_to_events()
    
    def _subscribe_to_events(self) -> None:
        """Subscribe to all events in subscriptions list."""
        for event_name in self._subscriptions:
            subscription_id = self._event_bus.subscribe(
                event_name=event_name,
                handler=self._on_event_received,
                scope="STRATEGY",
                strategy_id=self._strategy_id
            )
            self._subscription_ids.append(subscription_id)
    
    def _on_event_received(
        self, 
        event_name: str, 
        payload: BaseModel | None
    ) -> None:
        """
        Handle event notification from EventBus.
        
        Called by EventBus when a subscribed event is published.
        
        Args:
            event_name: Name of the published event
            payload: Optional event payload (System DTO or None)
        """
        # Map event to worker handler method
        handler_method_name = self._handler_mapping.get(event_name)
        
        if not handler_method_name:
            # Should never happen (only subscribed to mapped events)
            raise ValueError(
                f"No handler mapping for event '{event_name}' "
                f"in component '{self._component_id}'"
            )
        
        # Invoke worker method
        handler_method = getattr(self._worker, handler_method_name)
        envelope = handler_method(payload) if payload else handler_method()
        
        # Validate return type
        if not isinstance(envelope, DispositionEnvelope):
            raise TypeError(
                f"Worker method '{handler_method_name}' must return "
                f"DispositionEnvelope, got {type(envelope)}"
            )
        
        # Execute disposition
        self._handle_disposition(envelope, event_name)
    
    def _handle_disposition(
        self, 
        envelope: DispositionEnvelope,
        triggering_event: str
    ) -> None:
        """
        Execute action based on worker's disposition.
        
        Args:
            envelope: Worker's output envelope
            triggering_event: Event that triggered this worker
        """
        if envelope.disposition == "CONTINUE":
            self._handle_continue_disposition()
        
        elif envelope.disposition == "PUBLISH":
            self._handle_publish_disposition(envelope)
        
        elif envelope.disposition == "STOP":
            self._handle_stop_disposition()
        
        else:
            # Should never happen (Literal type validated by Pydantic)
            raise ValueError(f"Unknown disposition: {envelope.disposition}")
    
    def _handle_continue_disposition(self) -> None:
        """
        Handle CONTINUE disposition.
        
        Publishes system event to trigger next worker(s) in chain.
        Data passed via TickCache, not event payload.
        """
        system_event_name = self._generate_system_event_name()
        
        self._event_bus.publish(
            event_name=system_event_name,
            payload=None,  # Data in TickCache
            scope="STRATEGY",
            strategy_id=self._strategy_id
        )
    
    def _handle_publish_disposition(
        self, 
        envelope: DispositionEnvelope
    ) -> None:
        """
        Handle PUBLISH disposition.
        
        Validates custom event is allowed, then publishes with payload.
        
        Args:
            envelope: Envelope with event_name and optional event_payload
        
        Raises:
            ValueError: If event_name not in allowed_publications
        """
        # Validate event is declared in manifest
        self._validate_custom_event(envelope.event_name)
        
        # Publish custom event
        self._event_bus.publish(
            event_name=envelope.event_name,
            payload=envelope.event_payload,
            scope="STRATEGY",
            strategy_id=self._strategy_id
        )
    
    def _handle_stop_disposition(self) -> None:
        """
        Handle STOP disposition.
        
        Publishes flow-stop event to trigger cleanup.
        FlowTerminator component handles TickCache cleanup.
        """
        stop_event_name = self._generate_stop_event_name()
        
        self._event_bus.publish(
            event_name=stop_event_name,
            payload=None,
            scope="STRATEGY",
            strategy_id=self._strategy_id
        )
    
    def _generate_system_event_name(self) -> str:
        """
        Generate UUID-based system event name.
        
        Format: _{component_id}_output_{uuid}
        
        Returns:
            System event name (e.g., "_ema_detector_instance_1_output_a1b2c3d4")
        """
        unique_id = str(uuid4())[:8]
        return f"_{self._component_id}_output_{unique_id}"
    
    def _generate_stop_event_name(self) -> str:
        """
        Generate flow-stop event name.
        
        Format: _{strategy_id}_flow_stop_{uuid}
        
        Returns:
            Stop event name (e.g., "_btc_momentum_flow_stop_xyz789")
        """
        unique_id = str(uuid4())[:8]
        return f"_{self._strategy_id}_flow_stop_{unique_id}"
    
    def _validate_custom_event(self, event_name: str) -> None:
        """
        Validate worker is allowed to publish this custom event.
        
        Args:
            event_name: Custom event name to validate
        
        Raises:
            ValueError: If event_name not in allowed_publications
        """
        if event_name not in self._allowed_publications:
            raise ValueError(
                f"Worker '{self._component_id}' attempted to publish "
                f"undeclared event '{event_name}'. "
                f"Allowed events: {sorted(self._allowed_publications)}"
            )
    
    def shutdown(self) -> None:
        """
        Graceful shutdown and cleanup.
        
        Unsubscribes from all events. Called during strategy teardown.
        """
        for subscription_id in self._subscription_ids:
            try:
                self._event_bus.unsubscribe(subscription_id)
            except Exception:
                # Log error but continue cleanup
                pass
        
        self._subscription_ids.clear()
```

---

## EventWiringFactory Design

### Purpose

Creates EventAdapter instances and wires them to EventBus during bootstrap.

**Location:** `backend/assembly/event_wiring_factory.py`

```python
from typing import Dict, List
from backend.assembly.event_adapter import EventAdapter
from backend.core.interfaces.eventbus import IEventBus
from backend.core.interfaces.worker import IWorker


class EventWiringFactory:
    """
    Factory for creating and wiring EventAdapters.
    
    Reads wiring_map.yaml (generated by UI) and creates EventAdapter
    instances for each worker/component, subscribing them to EventBus.
    
    Responsibilities:
        - Parse wiring_map.yaml
        - Create EventAdapter per worker
        - Wire adapters to EventBus
        - Return adapter registry for lifecycle management
    """
    
    def __init__(self, event_bus: IEventBus):
        """
        Initialize EventWiringFactory.
        
        Args:
            event_bus: Platform EventBus singleton
        """
        self._event_bus = event_bus
    
    def create_adapters(
        self,
        strategy_id: str,
        workers: Dict[str, IWorker],
        wiring_config: Dict
    ) -> Dict[str, EventAdapter]:
        """
        Create EventAdapters for all workers in strategy.
        
        Args:
            strategy_id: Strategy identifier
            workers: Map of component_id → worker instance
            wiring_config: Parsed wiring_map.yaml for this strategy
        
        Returns:
            Map of component_id → EventAdapter instance
        
        Example:
            >>> workers = {
            ...     "ema_detector_instance_1": ema_worker,
            ...     "regime_classifier_instance_1": regime_worker
            ... }
            >>> wiring_config = {
            ...     "wiring_rules": [
            ...         {
            ...             "source": {"component_id": "ema_detector_instance_1", ...},
            ...             "target": {"component_id": "regime_classifier_instance_1", ...}
            ...         }
            ...     ]
            ... }
            >>> adapters = factory.create_adapters(
            ...     strategy_id="btc_momentum",
            ...     workers=workers,
            ...     wiring_config=wiring_config
            ... )
        """
        adapters = {}
        
        # Build subscription map per worker
        subscription_map = self._build_subscription_map(wiring_config)
        
        # Build allowed publications per worker (from manifests)
        publications_map = self._build_publications_map(workers)
        
        # Create adapter for each worker
        for component_id, worker in workers.items():
            adapter = EventAdapter(
                component_id=component_id,
                worker=worker,
                event_bus=self._event_bus,
                strategy_id=strategy_id,
                subscriptions=subscription_map.get(component_id, []),
                handler_mapping=self._build_handler_mapping(
                    component_id, 
                    wiring_config
                ),
                allowed_publications=publications_map.get(component_id, set())
            )
            
            adapters[component_id] = adapter
        
        return adapters
    
    def _build_subscription_map(
        self, 
        wiring_config: Dict
    ) -> Dict[str, List[str]]:
        """
        Build map of component_id → [event_names to subscribe to].
        
        Extracts target components from wiring rules.
        
        Args:
            wiring_config: Parsed wiring_map.yaml
        
        Returns:
            Map of component_id → list of event names
        
        Example:
            {
                "regime_classifier_instance_1": [
                    "_ema_detector_output_abc123",
                    "_tick_flow_start_def456"
                ]
            }
        """
        subscription_map = {}
        
        for rule in wiring_config.get("wiring_rules", []):
            target_id = rule["target"]["component_id"]
            source_event = rule["source"]["event_name"]
            
            if target_id not in subscription_map:
                subscription_map[target_id] = []
            
            subscription_map[target_id].append(source_event)
        
        return subscription_map
    
    def _build_handler_mapping(
        self,
        component_id: str,
        wiring_config: Dict
    ) -> Dict[str, str]:
        """
        Build event_name → handler_method mapping for component.
        
        Args:
            component_id: Component to build mapping for
            wiring_config: Parsed wiring_map.yaml
        
        Returns:
            Map of event_name → handler_method_name
        
        Example:
            {
                "_ema_detector_output_abc123": "process",
                "EMERGENCY_HALT": "on_emergency_halt"
            }
        """
        handler_mapping = {}
        
        for rule in wiring_config.get("wiring_rules", []):
            if rule["target"]["component_id"] == component_id:
                event_name = rule["source"]["event_name"]
                handler_method = rule["target"]["handler_method"]
                handler_mapping[event_name] = handler_method
        
        return handler_mapping
    
    def _build_publications_map(
        self,
        workers: Dict[str, IWorker]
    ) -> Dict[str, Set[str]]:
        """
        Build map of component_id → allowed custom events.
        
        Extracts 'publishes' list from worker manifests.
        
        Args:
            workers: Map of component_id → worker instance
        
        Returns:
            Map of component_id → set of allowed event names
        
        Example:
            {
                "momentum_scout_instance_1": {
                    "MOMENTUM_OPPORTUNITY",
                    "MOMENTUM_LOST"
                }
            }
        """
        publications_map = {}
        
        for component_id, worker in workers.items():
            # Get manifest from worker (workers store manifest reference)
            manifest = getattr(worker, '_manifest', None)
            
            if manifest and hasattr(manifest, 'publishes'):
                publications_map[component_id] = set(manifest.publishes)
            else:
                publications_map[component_id] = set()
        
        return publications_map
```

---

## Configuration Format

### wiring_map.yaml Structure

Generated by UI based on worker definitions:

```yaml
strategy_wiring_id: "btc_momentum_strategy_wiring"
strategy_ref: "btc_momentum_long"

wiring_rules:
  # Tick flow start → First context worker
  - wiring_id: "tick_to_ema"
    source:
      component_id: "tick_cache_manager"
      event_name: "_tick_flow_start_abc123"
      event_type: "SystemEvent"
    target:
      component_id: "ema_detector_instance_1"
      handler_method: "process"
  
  # EMA → Regime (context chain)
  - wiring_id: "ema_to_regime"
    source:
      component_id: "ema_detector_instance_1"
      event_name: "_ema_detector_output_def456"  # UUID-based
      event_type: "SystemEvent"
    target:
      component_id: "regime_classifier_instance_1"
      handler_method: "process"
  
  # Opportunity signal → Strategy Planner
  - wiring_id: "momentum_to_planner"
    source:
      component_id: "momentum_scout_instance_1"
      event_name: "MOMENTUM_OPPORTUNITY"  # Custom event
      event_type: "CustomEvent"
    target:
      component_id: "momentum_planner_instance_1"
      handler_method: "on_opportunity"
  
  # Emergency halt (multi-subscriber example)
  - wiring_id: "threat_to_emergency_1"
    source:
      component_id: "drawdown_monitor_instance_1"
      event_name: "EMERGENCY_HALT"
      event_type: "CustomEvent"
    target:
      component_id: "emergency_executor_instance_1"
      handler_method: "on_emergency_halt"
  
  - wiring_id: "threat_to_emergency_2"
    source:
      component_id: "drawdown_monitor_instance_1"
      event_name: "EMERGENCY_HALT"
      event_type: "CustomEvent"
    target:
      component_id: "position_closer_instance_1"
      handler_method: "on_emergency_halt"
```

---

## Worker Integration Pattern

### Worker Implementation (Bus-Agnostic)

```python
# plugins/context_workers/ema_detector/worker.py
from backend.core.interfaces.worker import IWorker, IWorkerLifecycle
from backend.dtos.shared.disposition_envelope import DispositionEnvelope

class EMADetector(IWorker, IWorkerLifecycle):
    """EMA detection worker - completely bus-agnostic."""
    
    def __init__(self, manifest: PluginManifest, params: EMAParams):
        self._manifest = manifest
        self._params = params
        self._cache = None
    
    @property
    def name(self) -> str:
        return self._manifest.plugin_id
    
    def initialize(self, strategy_cache: IStrategyCache, **capabilities) -> None:
        """Two-phase initialization."""
        self._cache = strategy_cache
    
    def process(self) -> DispositionEnvelope:
        """
        Main processing method - called by EventAdapter.
        
        Worker is UNAWARE of:
        - EventBus existence
        - EventAdapter existence
        - Other workers in chain
        - Event names or wiring
        
        Worker only knows:
        - Read data from TickCache (via IStrategyCache)
        - Perform calculation
        - Store result in TickCache
        - Return CONTINUE disposition
        """
        # 1. Read tick data from TickCache
        tick = self._cache.get_current_tick()
        
        # 2. Calculate EMA
        ema_value = self._calculate_ema(tick.close, self._params.period)
        
        # 3. Store result in TickCache
        result_dto = EMAOutputDTO(ema_value=ema_value)
        self._cache.set_result_dto(self, result_dto)
        
        # 4. Return CONTINUE (EventAdapter handles flow routing)
        return DispositionEnvelope(disposition="CONTINUE")
    
    def shutdown(self) -> None:
        """Cleanup."""
        pass
```

### EventAdapter Bridges Worker ↔ EventBus

```python
# EventAdapter receives event from EventBus
def _on_event_received(self, event_name: str, payload: BaseModel | None):
    # Call worker.process() (worker is bus-agnostic)
    envelope = self._worker.process()
    
    # Interpret disposition and publish events
    if envelope.disposition == "CONTINUE":
        # Generate system event for next worker
        system_event = f"_{self._component_id}_output_{uuid4()[:8]}"
        self._event_bus.publish(system_event, None, "STRATEGY", self._strategy_id)
```

---

## Complete Flow Example

### Scenario: EMA → Regime → Momentum Chain

**Workers:**
1. `ema_detector_instance_1` - Calculates EMA
2. `regime_classifier_instance_1` - Classifies market regime
3. `momentum_scout_instance_1` - Detects momentum opportunities

**Sequence:**

```mermaid
sequenceDiagram
    participant TCM as TickCacheManager
    participant Bus as EventBus
    participant A1 as EventAdapter<br/>(EMA)
    participant W1 as EMA Worker
    participant A2 as EventAdapter<br/>(Regime)
    participant W2 as Regime Worker
    participant A3 as EventAdapter<br/>(Momentum)
    participant W3 as Momentum Worker
    
    Note over TCM: New tick arrives
    TCM->>Bus: publish("_tick_flow_start_abc123", None)
    
    Note over Bus,A1: EMA subscribed to tick_flow_start
    Bus->>A1: on_event("_tick_flow_start_abc123", None)
    A1->>W1: process()
    W1->>W1: Calculate EMA, store in TickCache
    W1-->>A1: DispositionEnvelope(CONTINUE)
    A1->>A1: Generate "_ema_detector_output_def456"
    A1->>Bus: publish("_ema_detector_output_def456", None)
    
    Note over Bus,A2: Regime subscribed to ema_output
    Bus->>A2: on_event("_ema_detector_output_def456", None)
    A2->>W2: process()
    W2->>W2: Read EMA from TickCache<br/>Classify regime, store result
    W2-->>A2: DispositionEnvelope(CONTINUE)
    A2->>A2: Generate "_regime_classifier_output_ghi789"
    A2->>Bus: publish("_regime_classifier_output_ghi789", None)
    
    Note over Bus,A3: Momentum subscribed to regime_output
    Bus->>A3: on_event("_regime_classifier_output_ghi789", None)
    A3->>W3: process()
    W3->>W3: Read EMA+Regime from TickCache<br/>Detect momentum
    W3-->>A3: DispositionEnvelope(PUBLISH, "MOMENTUM_OPPORTUNITY", signal)
    A3->>A3: Validate "MOMENTUM_OPPORTUNITY" in manifest
    A3->>Bus: publish("MOMENTUM_OPPORTUNITY", OpportunitySignal)
    
    Note over Bus: Strategy Planner receives signal
```

**Key Points:**
- Workers are completely bus-agnostic
- EventAdapters handle all event plumbing
- System events auto-generated with UUIDs
- Custom events validated against manifest
- Data flows through TickCache, not event payloads

---

## Testing Strategy

### Unit Tests

**Test EventAdapter:**

```python
# tests/unit/assembly/test_event_adapter.py
import pytest
from unittest.mock import Mock, patch
from backend.assembly.event_adapter import EventAdapter
from backend.dtos.shared.disposition_envelope import DispositionEnvelope

def test_event_adapter_subscribes_on_init():
    """EventAdapter subscribes to all events on initialization."""
    mock_bus = Mock()
    mock_worker = Mock()
    
    adapter = EventAdapter(
        component_id="test_worker",
        worker=mock_worker,
        event_bus=mock_bus,
        strategy_id="test_strategy",
        subscriptions=["EVENT_A", "EVENT_B"],
        handler_mapping={"EVENT_A": "process", "EVENT_B": "process"},
        allowed_publications=set()
    )
    
    assert mock_bus.subscribe.call_count == 2
    # Verify subscriptions
    calls = mock_bus.subscribe.call_args_list
    assert calls[0][1]["event_name"] == "EVENT_A"
    assert calls[1][1]["event_name"] == "EVENT_B"

def test_event_adapter_invokes_worker_on_event():
    """EventAdapter invokes worker method when event received."""
    mock_bus = Mock()
    mock_worker = Mock()
    mock_worker.process.return_value = DispositionEnvelope(disposition="CONTINUE")
    
    adapter = EventAdapter(
        component_id="test_worker",
        worker=mock_worker,
        event_bus=mock_bus,
        strategy_id="test_strategy",
        subscriptions=["EVENT_A"],
        handler_mapping={"EVENT_A": "process"},
        allowed_publications=set()
    )
    
    # Simulate event
    adapter._on_event_received("EVENT_A", None)
    
    # Verify worker called
    mock_worker.process.assert_called_once()

def test_event_adapter_publishes_system_event_on_continue():
    """EventAdapter publishes system event for CONTINUE disposition."""
    mock_bus = Mock()
    mock_worker = Mock()
    mock_worker.process.return_value = DispositionEnvelope(disposition="CONTINUE")
    
    adapter = EventAdapter(
        component_id="test_worker",
        worker=mock_worker,
        event_bus=mock_bus,
        strategy_id="test_strategy",
        subscriptions=["EVENT_A"],
        handler_mapping={"EVENT_A": "process"},
        allowed_publications=set()
    )
    
    # Simulate event
    adapter._on_event_received("EVENT_A", None)
    
    # Verify system event published
    publish_calls = [c for c in mock_bus.publish.call_args_list 
                     if not c[1]["event_name"].startswith("_tick")]
    assert len(publish_calls) == 1
    assert publish_calls[0][1]["event_name"].startswith("_test_worker_output_")

def test_event_adapter_validates_custom_events():
    """EventAdapter rejects undeclared custom events."""
    mock_bus = Mock()
    mock_worker = Mock()
    mock_worker.process.return_value = DispositionEnvelope(
        disposition="PUBLISH",
        event_name="UNDECLARED_EVENT"
    )
    
    adapter = EventAdapter(
        component_id="test_worker",
        worker=mock_worker,
        event_bus=mock_bus,
        strategy_id="test_strategy",
        subscriptions=["EVENT_A"],
        handler_mapping={"EVENT_A": "process"},
        allowed_publications={"DECLARED_EVENT"}  # Not UNDECLARED_EVENT
    )
    
    # Should raise ValueError
    with pytest.raises(ValueError, match="undeclared event"):
        adapter._on_event_received("EVENT_A", None)

def test_event_adapter_publishes_custom_event_with_payload():
    """EventAdapter publishes custom event with payload."""
    mock_bus = Mock()
    mock_worker = Mock()
    mock_signal = Mock(spec=BaseModel)
    mock_worker.process.return_value = DispositionEnvelope(
        disposition="PUBLISH",
        event_name="MOMENTUM_OPPORTUNITY",
        event_payload=mock_signal
    )
    
    adapter = EventAdapter(
        component_id="test_worker",
        worker=mock_worker,
        event_bus=mock_bus,
        strategy_id="test_strategy",
        subscriptions=["EVENT_A"],
        handler_mapping={"EVENT_A": "process"},
        allowed_publications={"MOMENTUM_OPPORTUNITY"}
    )
    
    adapter._on_event_received("EVENT_A", None)
    
    # Verify custom event published with payload
    publish_calls = [c for c in mock_bus.publish.call_args_list]
    assert any(
        c[1]["event_name"] == "MOMENTUM_OPPORTUNITY" and 
        c[1]["payload"] == mock_signal
        for c in publish_calls
    )

def test_event_adapter_cleanup_on_shutdown():
    """EventAdapter unsubscribes all events on shutdown."""
    mock_bus = Mock()
    mock_bus.subscribe.side_effect = ["sub_1", "sub_2"]
    mock_worker = Mock()
    
    adapter = EventAdapter(
        component_id="test_worker",
        worker=mock_worker,
        event_bus=mock_bus,
        strategy_id="test_strategy",
        subscriptions=["EVENT_A", "EVENT_B"],
        handler_mapping={"EVENT_A": "process", "EVENT_B": "process"},
        allowed_publications=set()
    )
    
    adapter.shutdown()
    
    # Verify unsubscribe called for all subscriptions
    assert mock_bus.unsubscribe.call_count == 2
    mock_bus.unsubscribe.assert_any_call("sub_1")
    mock_bus.unsubscribe.assert_any_call("sub_2")
```

**Test EventWiringFactory:**

```python
# tests/unit/assembly/test_event_wiring_factory.py
def test_event_wiring_factory_creates_adapters_for_all_workers():
    """Factory creates one adapter per worker."""
    mock_bus = Mock()
    factory = EventWiringFactory(mock_bus)
    
    workers = {
        "worker_1": Mock(spec=IWorker),
        "worker_2": Mock(spec=IWorker)
    }
    
    wiring_config = {
        "wiring_rules": [
            {
                "source": {"component_id": "tick_manager", "event_name": "TICK"},
                "target": {"component_id": "worker_1", "handler_method": "process"}
            }
        ]
    }
    
    adapters = factory.create_adapters("strategy_1", workers, wiring_config)
    
    assert len(adapters) == 2
    assert "worker_1" in adapters
    assert "worker_2" in adapters

def test_event_wiring_factory_builds_subscription_map():
    """Factory correctly maps events to target workers."""
    factory = EventWiringFactory(Mock())
    
    wiring_config = {
        "wiring_rules": [
            {
                "source": {"event_name": "EVENT_A"},
                "target": {"component_id": "worker_1"}
            },
            {
                "source": {"event_name": "EVENT_B"},
                "target": {"component_id": "worker_1"}
            },
            {
                "source": {"event_name": "EVENT_C"},
                "target": {"component_id": "worker_2"}
            }
        ]
    }
    
    subscription_map = factory._build_subscription_map(wiring_config)
    
    assert subscription_map["worker_1"] == ["EVENT_A", "EVENT_B"]
    assert subscription_map["worker_2"] == ["EVENT_C"]
```

### Integration Tests

**Test Full Flow:**

```python
# tests/integration/test_event_driven_flow.py
def test_ema_to_regime_flow():
    """Test complete EMA → Regime worker chain via EventAdapters."""
    # Setup
    event_bus = EventBus()
    ema_worker = EMADetector(manifest, params)
    regime_worker = RegimeClassifier(manifest, params)
    
    # Initialize workers
    strategy_cache = create_test_strategy_cache()
    ema_worker.initialize(strategy_cache)
    regime_worker.initialize(strategy_cache)
    
    # Create adapters
    factory = EventWiringFactory(event_bus)
    wiring_config = load_test_wiring_config("ema_to_regime.yaml")
    
    adapters = factory.create_adapters(
        strategy_id="test_strategy",
        workers={
            "ema_instance": ema_worker,
            "regime_instance": regime_worker
        },
        wiring_config=wiring_config
    )
    
    # Trigger flow
    event_bus.publish("_tick_flow_start", None, "STRATEGY", "test_strategy")
    
    # Verify chain executed
    assert strategy_cache.has_result("ema_instance")
    assert strategy_cache.has_result("regime_instance")
```

---

## Dependencies

### Imports

```python
# backend/assembly/event_adapter.py
from uuid import uuid4
from typing import Dict, Set, Callable
from pydantic import BaseModel

from backend.core.interfaces.eventbus import IEventBus
from backend.core.interfaces.worker import IWorker
from backend.dtos.shared.disposition_envelope import DispositionEnvelope
```

### Required Components

**Already Implemented:**
- ✅ EventBus (`backend/core/eventbus.py`)
- ✅ IEventBus protocol (`backend/core/interfaces/eventbus.py`)
- ✅ IWorker protocol (`backend/core/interfaces/worker.py`)
- ✅ DispositionEnvelope DTO (`backend/dtos/shared/disposition_envelope.py`)

**To Be Implemented:**
- ⏳ Workers (Phase 2+)
- ⏳ wiring_map.yaml parser (ConfigLoader)
- ⏳ PluginManifest with publishes field

---

## Open Questions

### 1. System Event Name Persistence

**Question:** Should system event names (UUID-based) be persisted across runs?

**Options:**
- **A. Generate new UUIDs each run** (current design)
  - Pros: Simple, no state management
  - Cons: Can't replay exact event sequence
  
- **B. Persist event names in wiring_map.yaml**
  - Pros: Deterministic event names, replay-friendly
  - Cons: UI must manage UUID generation

**Recommendation:** Start with Option A (generate fresh), revisit if replay becomes critical.

### 2. Handler Method Validation

**Question:** Should EventAdapter validate handler method exists at construction time?

**Current:** Validation happens when event is received (runtime)

**Alternative:** Validate during adapter creation (fail-fast)

```python
def __init__(self, ...):
    # Validate all handler methods exist
    for event_name, method_name in handler_mapping.items():
        if not hasattr(self._worker, method_name):
            raise ValueError(f"Worker missing handler method: {method_name}")
```

**Recommendation:** Add fail-fast validation (better developer experience).

### 3. Multi-Handler Support

**Question:** Should workers support multiple handler methods, or just `process()`?

**Current Design:** Flexible mapping (event → any method name)

**Example:**
```python
handler_mapping = {
    "_tick_flow_start": "process",
    "EMERGENCY_HALT": "on_emergency_halt",
    "MOMENTUM_OPPORTUNITY": "on_opportunity"
}
```

**Recommendation:** Keep flexible (supports future StrategyPlanner with multiple handlers).

---

## Implementation Checklist

- [ ] Implement `EventAdapter` class
  - [ ] `__init__` with subscription setup
  - [ ] `_on_event_received` event handler
  - [ ] `_handle_disposition` dispatcher
  - [ ] `_handle_continue_disposition`
  - [ ] `_handle_publish_disposition`
  - [ ] `_handle_stop_disposition`
  - [ ] `_generate_system_event_name`
  - [ ] `_generate_stop_event_name`
  - [ ] `_validate_custom_event`
  - [ ] `shutdown` cleanup

- [ ] Implement `EventWiringFactory`
  - [ ] `create_adapters` main factory method
  - [ ] `_build_subscription_map`
  - [ ] `_build_handler_mapping`
  - [ ] `_build_publications_map`

- [ ] Unit Tests (EventAdapter)
  - [ ] Subscription on init
  - [ ] Worker invocation
  - [ ] CONTINUE disposition
  - [ ] PUBLISH disposition (valid)
  - [ ] PUBLISH disposition (invalid event)
  - [ ] STOP disposition
  - [ ] Shutdown cleanup

- [ ] Unit Tests (EventWiringFactory)
  - [ ] Adapter creation
  - [ ] Subscription map building
  - [ ] Handler mapping building
  - [ ] Publications map building

- [ ] Integration Tests
  - [ ] Full worker chain flow
  - [ ] Custom event publication
  - [ ] Multi-subscriber events

- [ ] Documentation
  - [ ] Docstrings
  - [ ] Architecture docs update
  - [ ] Usage examples

---

## Related Documentation

- **EventBus Implementation:** [../development/#Archief/EVENTBUS_DESIGN.md](../development/#Archief/EVENTBUS_DESIGN.md)
- **IWorkerLifecycle:** [../development/#Archief/IWORKERLIFECYCLE_DESIGN.md](../development/#Archief/IWORKERLIFECYCLE_DESIGN.md)
- **DispositionEnvelope:** [backend/dtos/shared/disposition_envelope.py](../../backend/dtos/shared/disposition_envelope.py)
- **Event-Driven Wiring:** [../architecture/EVENT_DRIVEN_WIRING.md](../architecture/EVENT_DRIVEN_WIRING.md)
- **Data Flow:** [../architecture/DATA_FLOW.md](../architecture/DATA_FLOW.md)
- **Platform Components:** [../architecture/PLATFORM_COMPONENTS.md](../architecture/PLATFORM_COMPONENTS.md)

---

**End of Design Document**
