# Architecture Gaps - Design Issues Analysis

**Status:** OPEN ISSUES - Requires Decisions  
**Created:** 2025-11-02  
**Priority:** CRITICAL - Must Resolve Before Implementation (Week 1)

---

## Purpose

This document identifies **architectural design flaws and inconsistencies** in the S1mpleTraderV3 design. These are NOT implementation gaps (missing code), but conceptual issues in the architecture itself that must be resolved before implementation begins.

**How to use this document:**
1. Review each gap individually
2. Discuss trade-offs of proposed solutions
3. Make explicit design decisions
4. Update relevant architecture docs with decisions
5. Archive this document when all gaps are resolved

---

## 🔴 CRITICAL GAPS (Must Fix Before Week 1)

### GAP-001: StrategyCache Singleton vs Multi-Strategy Execution ✅ RESOLVED

**Location:** `POINT_IN_TIME_MODEL.md`, `PLATFORM_COMPONENTS.md`

**Problem:**
StrategyCache was conceptualized as a singleton with reconfigure() method, creating race conditions in concurrent multi-strategy execution.

**Root Cause Analysis:**
The conflict arose from three architectural insights:

1. **EventBus Scope Filtering:** Platform-scoped events (e.g., market tick) can trigger MULTIPLE strategies simultaneously via scope filtering
2. **Point-in-Time Model:** Cache must be stateless - fresh dict per tick, cleared after run completion
3. **Bus-Agnostic Architecture:** ALL components (including FlowInitiator) are bus-agnostic and communicate via EventAdapters

**Key Realization:**
FlowInitiator (tick flow coordinator) CANNOT be singleton because:
- One RAW_TICK event (ScopeLevel.PLATFORM) triggers multiple strategies
- Each strategy needs isolated FlowInitiator + StrategyCache pair
- EventBus scope filtering (SubscriptionScope.should_receive_event) enables multi-strategy triggering

**DECISION: Per-Strategy Instances (Option B)**

**Architecture:**
```python
# backend/core/strategy_cache.py
class StrategyCache:
    """
    Per-strategy point-in-time DTO container (NOT singleton).
    
    Lifecycle: Created per strategy, injected into workers.
    Stateless: Fresh cache dict per tick, cleared after completion.
    """
    def __init__(self):
        self._current_cache: Dict[Type[BaseModel], BaseModel] = {}
        self._current_anchor: RunAnchor | None = None
    
    def start_new_strategy_run(
        self,
        strategy_cache: Dict[Type[BaseModel], BaseModel],
        timestamp: datetime
    ) -> None:
        """Reset cache for new tick (stateless)."""
        self._current_cache = strategy_cache
        self._current_anchor = RunAnchor(timestamp=timestamp)
    
    def clear_cache(self) -> None:
        """Clear after run completion (point-in-time principle)."""
        self._current_cache.clear()
        self._current_anchor = None
```

```python
# FlowInitiator: Per-strategy component (NOT singleton)
class FlowInitiator:
    """
    Per-strategy tick flow coordinator.
    
    Receives platform-scoped RAW_TICK via EventAdapter,
    resets StrategyCache, publishes STRATEGY_RUN_STARTED.
    """
    def __init__(self, strategy_cache: StrategyCache):
        self._cache = strategy_cache
    
    def on_raw_tick(self, tick_data: Dict) -> DispositionEnvelope:
        # Reset cache for new tick
        self._cache.start_new_strategy_run(
            strategy_cache={},
            timestamp=tick_data["timestamp"]
        )
        
        return DispositionEnvelope(
            disposition=Disposition.PUBLISH,
            event_name="STRATEGY_RUN_STARTED",  # System event
            payload=tick_data
        )

# backend/services/operation_service.py
class OperationService:
    """Lifecycle orchestrator - platte orkestratie (no StrategyFactory)."""
    
    def start_strategy(self, strategy_link: StrategyLink):
        # 1. Translate config to BuildSpecs
        buildspecs = ConfigTranslator.translate(
            blueprint=strategy_link.blueprint,
            wiring=strategy_link.wiring
        )
        
        # 2. FLAT ORCHESTRATION (readable, no factory hierarchy)
        # Create per-strategy components
        cache = StrategyCache()  # Per-strategy instance
        flow_initiator = FlowInitiator(cache)  # Per-strategy instance
        
        # Create workers via WorkerFactory (pure builder)
        workers = self._worker_factory.create_workforce(
            worker_specs=buildspecs.workers,
            strategy_cache=cache  # Inject per-strategy cache
        )
        
        # Create EventAdapters via EventWiringFactory (pure builder)
        adapters = self._wiring_factory.create_adapters(
            strategy_id=strategy_link.id,
            workers=workers,
            wiring_spec=buildspecs.wiring,
            event_bus=self._event_bus
        )
        
        # Wire FlowInitiator via EventAdapter (bus-agnostic)
        flow_adapter = EventAdapter(
            component_id="flow_initiator",
            worker=flow_initiator,
            event_bus=self._event_bus,
            strategy_id=strategy_link.id,
            subscriptions=["RAW_TICK"],  # Platform-scoped subscription
            handler_mapping={"RAW_TICK": "on_raw_tick"},
            system_event_publications={"CONTINUE": "STRATEGY_RUN_STARTED"}
        )
        adapters["flow_initiator"] = flow_adapter
        
        # 3. Store strategy instance
        self._strategies[strategy_link.id] = StrategyInstance(
            cache=cache,
            flow_initiator=flow_initiator,
            workers=workers,
            adapters=adapters
        )
```

**Multi-Strategy Concurrent Execution Flow:**
```python
# Platform-scoped producer publishes ONCE
market_adapter.publish(
    event_name="RAW_TICK",
    payload={"symbol": "BTC_EUR", "timestamp": ...},
    scope=ScopeLevel.PLATFORM,
    strategy_instance_id=None  # Platform scope
)

# EventBus scope filtering triggers MULTIPLE FlowInitiators
# Strategy A's FlowInitiator
flow_initiator_a.on_raw_tick(payload)  # Resets cache_a

# Strategy B's FlowInitiator
flow_initiator_b.on_raw_tick(payload)  # Resets cache_b

# Both strategies run concurrently with isolated caches
```

**Rationale:**
1. ✅ **Perfect isolation** - Each strategy has dedicated cache + FlowInitiator
2. ✅ **Simpler API** - Workers don't need strategy_id parameter
3. ✅ **Clear lifecycle** - Cache created per strategy, injected via DI
4. ✅ **Bus-agnostic consistency** - FlowInitiator treated like any Worker (EventAdapter pattern)
5. ✅ **Platte orkestratie** - No StrategyFactory hierarchy, direct assembly in OperationService
6. ✅ **YAGNI** - No premature abstraction, readable top-to-bottom flow

**Architectural Implications:**
- **Factory Uniformity:** ALL event-driven components (Workers, FlowInitiator, Adapters) use EventAdapter pattern
- **No StrategyFactory:** Assembly happens directly in OperationService (flat orchestration)
- **DRY Trade-off:** Pragmatic choice - leesbaarheid > abstractie voor 10-15 regels assembly code
- **Singleton Redefinition:** Platform singletons (EventBus, PluginRegistry) vs Per-Strategy components (Cache, FlowInitiator, Workers)

**Decision:** ✅ **APPROVED - Per-Strategy Instances + Flat Orchestration**

**Impact:**
- ✅ IStrategyCache protocol - no changes needed (already per-instance design)
- ✅ Worker initialization - cache injection via WorkerFactory
- ✅ OperationService - flat orchestration (no StrategyFactory)
- ⚠️ POINT_IN_TIME_MODEL.md - clarify StrategyCache is per-strategy
- ⚠️ PLATFORM_COMPONENTS.md - update singleton definition

---

### GAP-002: Event-Centric Connector Architecture ✅ RESOLVED

**Location:** `EVENT_DRIVEN_WIRING.md`, `PLUGIN_ANATOMY.md`

**Problem:**
Unclear how workers remain bus-agnostic while supporting both system flow control events and custom business events. Three core questions:
1. How do workers declare their inputs/outputs without knowing EventBus?
2. How does the adapter know what payload types to expect/produce?
3. How do we validate wiring at bootstrap without runtime overhead?

**Root Cause Analysis:**
Missing **complete connector abstraction** with payload type declarations and event-centric wiring model.

**DECISION: Event-Centric Connector Architecture**

### **Architecture Principles**

1. **Workers are connector-based factories**
   - Declare abstract inputs/outputs in manifest (connectors)
   - Zero knowledge of EventBus, event names, or wiring
   - EventAdapter translates connectors ↔ events at runtime

2. **Event names are the interface**
   - Wiring rules connect events (not workers directly)
   - Adapters subscribe to event names, publish to event names
   - Workers can be replaced without touching consumers

3. **Bootstrap validation only**
   - Fail-fast during configuration load (~100ms one-time cost)
   - Zero runtime validation (thousands of events/second)
   - Trust bootstrap-validated configuration

4. **Uniform EventAdapter for ALL components**
   - Same implementation for workers, singletons, FlowInitiators
   - EventBus handles scope filtering (PLATFORM vs STRATEGY)
   - Configuration drives behavior (not adapter code)

---

### **Plugin Manifest Schema**

Workers declare abstract inputs/outputs without knowing events or wiring.

**Complete Example:**
```yaml
# plugins/signal_detectors/fvg_detector/manifest.yaml
plugin_id: "s1mple/fvg_detector/v1.0.0"
category: "signal_detector"

dependencies:
  requires_dtos:
    - source: "backend.dto_reg.s1mple.ema_detector.v1_0_0.ema_output_dto"
      dto_class: "EMAOutputDTO"
  
  produces_dtos:
    - dto_class: "FVGAnalysisDTO"
      local_path: "dtos/fvg_analysis_dto.py"

inputs:
  - connector_id: "default_trigger"
    handler_method: "process"

outputs:
  # Flow control (no payload)
  - connector_id: "completion"
    disposition: "CONTINUE"
    payload_type: null
  
  # System DTO output (Signal, Risk, StrategyDirective, etc.)
  - connector_id: "signal_detected"
    disposition: "PUBLISH"
    payload_type: "Signal"
    payload_source: "backend.dtos.strategy.signal.Signal"
  
  # Custom DTO output (from produces_dtos)
  - connector_id: "analysis_broadcast"
    disposition: "PUBLISH"
    payload_type: "FVGAnalysisDTO"
    payload_source: "local"  # References produces_dtos
```

**Manifest Fields:**

**dependencies:**
- `requires_dtos`: TickCache DTOs this worker reads (via `get_required_dtos()`)
- `produces_dtos`: TickCache DTOs this worker writes (via `set_result_dto()`)

**inputs:**
- `connector_id`: Unique identifier for this input
- `handler_method`: Method name on worker class to invoke

**outputs:**
- `connector_id`: Unique identifier for this output
- `disposition`: `CONTINUE` (flow control) or `PUBLISH` (event broadcast)
- `payload_type`: DTO class name (null for no payload)
- `payload_source`: Import path or "local" for produces_dtos DTOs

---

### **Worker Implementation: Bus-Agnostic**

Workers know NOTHING about events, EventBus, or wiring:

```python
class FVGDetector(IWorker):
    """
    Worker knows:
    ✓ Handler method names from manifest (process)
    ✓ Connector IDs from manifest (completion, signal_detected, analysis_broadcast)
    ✓ DTO types it produces/consumes
    
    Worker does NOT know:
    ✗ Event names
    ✗ EventBus existence
    ✗ Other workers
    ✗ Wiring configuration
    """
    
    def process(self) -> DispositionEnvelope:
        # Get TickCache DTOs (dependency resolution)
        ema_data = self.strategy_cache.get_required_dtos()[EMAOutputDTO]
        
        # Perform analysis
        fvg_analysis = self._analyze_fvg(ema_data)
        
        # Store analysis DTO to TickCache
        self.strategy_cache.set_result_dto(fvg_analysis)
        
        if fvg_analysis.signal_strength > 0.8:
            # PUBLISH with System DTO payload
            # Worker does NOT know event name - EventAdapter handles routing
            return DispositionEnvelope(
                disposition=Disposition.PUBLISH,
                connector_id="signal_detected",  # From manifest
                payload=Signal(...)              # System DTO
            )
        
        # CONTINUE - proceed to next worker
        # Worker does NOT know which worker is next
        return DispositionEnvelope(
            disposition=Disposition.CONTINUE,
            connector_id="completion"  # From manifest
        )
```

**Key Points:**
- Worker returns `connector_id` (from its manifest), NOT event names
- Worker returns `payload` (DTO), NOT event-specific data
- EventAdapter translates connector_id → event_name (via wiring config)
- Worker is completely decoupled from event routing

---

### **Wiring Map Schema**

*(To be discussed - platform_wiring.yaml and strategy_wiring_map.yaml structure)*

---

### **Bootstrap Validation: Fail-Fast**

EventWiringFactory validates configuration ONCE at bootstrap:

```python
class EventWiringFactory:
    def create_adapters(
        self,
        strategy_id: str,
        workers: Dict[str, IWorker],
        wiring_spec: WiringSpec
    ) -> Dict[str, EventAdapter]:
        
        for rule in wiring_spec.wiring_rules:
            source_worker = workers[rule.source.component_id]
            target_worker = workers[rule.target.component_id]
            
            # ✅ Validate source connector exists in manifest
            source_connector = self._get_output_connector(
                source_worker.manifest,
                rule.source.connector_id
            )
            if not source_connector:
                raise ConfigurationError(
                    f"Connector {rule.source.connector_id} not found "
                    f"in {source_worker.manifest.plugin_id}"
                )
            
            # ✅ Validate target connector exists in manifest
            target_connector = self._get_input_connector(
                target_worker.manifest,
                rule.target.connector_id
            )
            if not target_connector:
                raise ConfigurationError(
                    f"Connector {rule.target.connector_id} not found "
                    f"in {target_worker.manifest.plugin_id}"
                )
            
            # ✅ Validate handler method exists on worker
            if not hasattr(target_worker, rule.target.handler_method):
                raise ConfigurationError(
                    f"Handler {rule.target.handler_method} not found "
                    f"on {target_worker.__class__.__name__}"
                )
            
            # ✅ Validate payload type compatibility
            if source_connector.payload_type != target_connector.payload_type:
                raise ConfigurationError(
                    f"Payload type mismatch: "
                    f"{rule.source.component_id}.{source_connector.connector_id} "
                    f"produces {source_connector.payload_type}, "
                    f"{rule.target.component_id}.{target_connector.connector_id} "
                    f"expects {target_connector.payload_type}"
                )
            
            # ✅ Validate payload_source can be imported
            if source_connector.payload_source:
                try:
                    self._import_class(source_connector.payload_source)
                except ImportError as e:
                    raise ConfigurationError(
                        f"Cannot import {source_connector.payload_source}: {e}"
                    )
        
        # ✅ Validate DTO dependencies
        for component_id, worker in workers.items():
            for required_dto in worker.manifest.dependencies.requires_dtos:
                if not self._dto_available(required_dto.source):
                    raise ConfigurationError(
                        f"{component_id} requires {required_dto.dto_class} "
                        f"from {required_dto.source} but it's not available"
                    )
        
        # If we reach here: Configuration is VALID
        # Build and return adapters (trust configuration at runtime)
        return self._build_adapters(strategy_id, workers, wiring_spec)
```

**Validation Checks:**
1. Connector existence (inputs/outputs in manifest)
2. Handler method existence (on worker class)
3. Payload type compatibility (source → target match)
4. Import validation (payload_source can be imported)
5. DTO dependency completeness (requires_dtos available)

**Performance:**
- Bootstrap: ~100ms one-time cost
- Runtime: ZERO validation overhead
- Result: Fail-fast safety without performance penalty

---

### **Runtime Execution: Zero Validation**

EventAdapter trusts bootstrap-validated configuration:

```python
class EventAdapter:
    def __init__(self, component: IWorker, config: AdapterConfig):
        self._component = component
        self._config = config  # Bootstrap-validated config
    
    def handle_event(self, event: Event):
        # NO validation here - trust bootstrap!
        subscription = self._config.get_subscription(event.name)
        handler = getattr(self._component, subscription.handler_method)
        
        # Call handler with payload (type already validated)
        result = handler(event.payload)
        
        # Process disposition
        self._handle_disposition(result)
    
    def _handle_disposition(self, envelope: DispositionEnvelope):
        if envelope.disposition == Disposition.CONTINUE:
            # Publish system event (no payload)
            publication = self._config.get_publication_for_connector(envelope.connector_id)
            self._bus.publish(
                publication.event_name,
                publication.scope,
                payload=None
            )
        
        elif envelope.disposition == Disposition.PUBLISH:
            # Publish event WITH payload (System DTO or Custom DTO)
            publication = self._config.get_publication_for_connector(envelope.connector_id)
            self._bus.publish(
                publication.event_name,
                publication.scope,
                payload=envelope.payload  # DTO travels in event
            )
```

---

### **System DTOs vs TickCache DTOs**

Two separate transport mechanisms with different purposes:

#### **System DTOs (via EventBus)**

**Purpose:** Flow control signals (Signal, Risk, StrategyDirective, EntryPlan, etc.)

**Transport:** DispositionEnvelope.payload → EventBus

```python
# Worker publishes Signal via PUBLISH disposition
return DispositionEnvelope(
    disposition=Disposition.PUBLISH,
    connector_id="signal_detected",  # From manifest
    payload=Signal(...)              # ← Travels in event payload
)

# EventAdapter translates connector_id → event_name (from wiring config)
# Then publishes to EventBus
self._bus.publish(
    event_name="SIGNAL_XYZ",  # From wiring config, NOT from worker
    scope=ScopeLevel.STRATEGY,
    payload=envelope.payload  # ← Signal in event
)

# Consumer receives via handler
def on_signal(self, signal: Signal):
    # Signal came directly from event payload
    self.plan_entry(signal)
```

**Manifest:**
```yaml
outputs:
  - connector_id: "signal_detected"
    disposition: "PUBLISH"
    payload_type: "Signal"
    payload_source: "backend.dtos.strategy.signal.Signal"
```

#### **TickCache DTOs (via StrategyCache)**

**Purpose:** Worker calculation results (EMAOutputDTO, MarketStructureDTO, etc.)

**Transport:** StrategyCache.set_result_dto() / get_required_dtos()

```python
# Worker stores calculation result to TickCache
result = EMAOutputDTO(fast=50.2, slow=51.1, ...)
self.strategy_cache.set_result_dto(result)

# Return CONTINUE (no event payload)
return DispositionEnvelope(disposition=Disposition.CONTINUE)

# Consumer retrieves from TickCache
def process(self):
    ema_data = self.strategy_cache.get_required_dtos()[EMAOutputDTO]
    # Use ema_data in calculation
```

**Manifest:**
```yaml
dependencies:
  produces_dtos:
    - dto_class: "EMAOutputDTO"
      local_path: "dtos/ema_output_dto.py"
  
  requires_dtos:
    - source: "backend.dto_reg.s1mple.ema_detector.v1_0_0.ema_output_dto"
      dto_class: "EMAOutputDTO"
```

**Key Difference:**
- **System DTOs:** Event-driven flow (Signal triggers Planning)
- **TickCache DTOs:** Dependency resolution (EMA data available for consumers)

---

### **Uniform EventAdapter Pattern**

ALL components use the same EventAdapter implementation:

**Components:**
- Strategy workers (SignalDetectors, ContextWorkers, etc.)
- Platform singletons (PositionManager, OrderRouter, etc.)
- FlowInitiators (per-strategy tick entry points)

**NO platform vs strategy adapter types:**

```python
# ✅ ONE EventAdapter implementation for ALL
class EventAdapter:
    def __init__(
        self,
        component: IWorker,
        bus: EventBus,
        config: AdapterConfig
    ):
        self._component = component
        self._bus = bus
        self._config = config  # Contains scope info
    
    def _publish(self, event_name: str, scope: ScopeLevel, payload: Any):
        # Scope from config (not hardcoded in adapter)
        self._bus.publish(event_name, scope, payload)
```

**Scope filtering in EventBus:**

```python
class EventBus:
    def publish(
        self,
        event_name: str,
        scope: ScopeLevel,
        payload: Any,
        strategy_id: str = None
    ):
        if scope == ScopeLevel.PLATFORM:
            # Broadcast to ALL strategies + platform subscribers
            self._publish_to_all_scopes(event_name, payload)
        elif scope == ScopeLevel.STRATEGY:
            # Publish only to specific strategy scope
            self._publish_to_strategy(event_name, payload, strategy_id)
```

**Result:**
- EventAdapter code is IDENTICAL for all components
- Scope filtering happens in EventBus (not adapter)
- Configuration determines behavior

---

**Decision:** ✅ **APPROVED - Event-Centric Connector Architecture**

**Impact:**
- ⚠️ PLUGIN_ANATOMY.md - Update manifest schema (inputs/outputs with connector_id, NO event_name)
- ⚠️ DispositionEnvelope - Change event_name field to connector_id
- ⚠️ EVENT_DRIVEN_WIRING.md - Document event-centric wiring
- ⚠️ ConfigTranslator - Parse wiring_rules
- ⚠️ EventWiringFactory - Implement bootstrap validation
- ⚠️ EventAdapter - Uniform implementation (no platform vs strategy types)
- ⚠️ EventBus - Scope filtering (PLATFORM/STRATEGY)
- ✅ Workers - Remain 100% bus-agnostic (no changes needed)

---

### GAP-003: PUBLISH Disposition - Payload Location Ambiguity

**Scenario:** EMADetector → MomentumScout → StrategyPlanner

#### **1. Manifests**

```yaml
# ema_detector manifest
outputs:
  - connector_id: "completion"
    disposition: "CONTINUE"
    payload_type: null

dependencies:
  produces_dtos:
    - dto_class: "EMAOutputDTO"
```

```yaml
# momentum_scout manifest
inputs:
  - connector_id: "default_trigger"
    handler_method: "process"
    payload_type: null

outputs:
  - connector_id: "signal_detected"
    disposition: "PUBLISH"
    event_name: "MOMENTUM_SIGNAL"
    payload_type: "Signal"
    payload_source: "backend.dtos.strategy.signal.Signal"

dependencies:
  requires_dtos:
    - source: "backend.dto_reg.s1mple.ema_detector.v1_0_0.ema_output_dto"
      dto_class: "EMAOutputDTO"
```

```yaml
# strategy_planner manifest
inputs:
  - connector_id: "signal_input"
    handler_method: "on_signal"
    payload_type: "Signal"
    payload_source: "backend.dtos.strategy.signal.Signal"
```

#### **2. Wiring Map**

```yaml
wiring_rules:
  - wiring_id: "ema_to_momentum"
    source:
      component_id: "ema_detector_instance_1"
      connector_id: "completion"
      event_name: "_EMA_READY"
      event_type: "SystemEvent"
    target:
      component_id: "momentum_scout_instance_1"
      connector_id: "default_trigger"
      handler_method: "process"
  
  - wiring_id: "momentum_to_planner"
    source:
      component_id: "momentum_scout_instance_1"
      connector_id: "signal_detected"
      event_name: "MOMENTUM_SIGNAL"
      event_type: "CustomEvent"
    target:
      component_id: "strategy_planner_instance_1"
      connector_id: "signal_input"
      handler_method: "on_signal"
```

#### **3. Bootstrap Validation**

```python
# EventWiringFactory validates:
# ✅ "completion" connector exists in ema_detector manifest
# ✅ "default_trigger" connector exists in momentum_scout manifest
# ✅ "process" method exists on MomentumScout class
# ✅ "signal_detected" connector exists in momentum_scout manifest
# ✅ "MOMENTUM_SIGNAL" payload types match (Signal → Signal)
# ✅ "on_signal" method exists on StrategyPlanner class
# ✅ EMAOutputDTO dependency available
# ✅ Signal import path valid

# Result: Configuration is VALID
```

#### **4. Runtime Execution**

```python
# Step 1: EMADetector processes
ema_detector.process()
# → Calculates EMA
# → Stores EMAOutputDTO to TickCache
# → Returns DispositionEnvelope(CONTINUE)
# → EventAdapter publishes "_EMA_READY" event (no payload)

# Step 2: EventBus routes "_EMA_READY"
momentum_scout_adapter.handle_event(Event("_EMA_READY", None))
# → Calls momentum_scout.process()

# Step 3: MomentumScout processes
momentum_scout.process()
# → Retrieves EMAOutputDTO from TickCache
# → Detects momentum
# → Returns DispositionEnvelope(PUBLISH, "MOMENTUM_SIGNAL", Signal(...))
# → EventAdapter publishes event WITH Signal payload

# Step 4: EventBus routes "MOMENTUM_SIGNAL"
strategy_planner_adapter.handle_event(Event("MOMENTUM_SIGNAL", Signal(...)))
# → Calls strategy_planner.on_signal(Signal(...))

# Step 5: StrategyPlanner processes
strategy_planner.on_signal(signal)
# → Receives Signal from event payload
# → Creates EntryPlan
# → Returns DispositionEnvelope(PUBLISH, "ENTRY_PLAN_READY", EntryPlan(...))
```

---

**Decision:** ✅ **APPROVED - Event-Centric Connector Architecture**

**Impact:**
- ⚠️ PLUGIN_ANATOMY.md - Update manifest schema (inputs/outputs with payload_type/payload_source)
- ⚠️ EVENT_DRIVEN_WIRING.md - Document event-centric wiring (event names are interface)
- ⚠️ ConfigTranslator - Parse wiring_rules with event-centric pattern
- ⚠️ EventWiringFactory - Implement bootstrap validation (6 checks)
- ⚠️ EventAdapter - Uniform implementation (no platform vs strategy types)
- ⚠️ EventBus - Scope filtering (PLATFORM/STRATEGY)
- ✅ Workers - Remain 100% bus-agnostic (no changes needed)

---

### GAP-003: PUBLISH Disposition - Payload Location Ambiguity

**Location:** `EVENT_DRIVEN_WIRING.md`, `WORKER_TAXONOMY.md`

**Problem:**
Documentation contradicts itself on where PUBLISH payload goes:

**EVENT_DRIVEN_WIRING.md says (V2 pattern):**
```yaml
# plugins/context_workers/ema_detector/manifest.yaml
plugin_id: "s1mple/ema_detector/v1.0.0"
category: "context_worker"

inputs:
  - connector_id: "default_trigger"  # Standard input
    type: "system"
    description: "Default processing trigger from previous worker or flow start"
    required: true

outputs:
  - connector_id: "completion"  # Standard CONTINUE output
    type: "system"
    description: "Signals completion for next worker in chain"
```

**UI Generation:**
```typescript
// Strategy Builder UI
class WiringManager {
    generateSystemEventName(worker: WorkerNode, connector: Connector): string {
        // Deterministic generation (NO UUID needed!)
        const generated = `_${worker.instanceId}_${connector.id}`;
        // Example: "_ema_detector_instance_1_completion"
        
        // User can rename in UI:
        return this.getUserOverride(generated) ?? generated;
        // Example: User renames to "_EMA_READY" for clarity
    }
}
```

**Generated Wiring:**
```yaml
# strategy_wiring_map.yaml
wiring_rules:
  - wiring_id: "ema_fast_to_ema_slow"
    source:
      component_id: "ema_detector_instance_1"
      connector_id: "completion"
      event_name: "_ema_detector_instance_1_completion"  # UI generated
      # OR: "_EMA_READY" (user renamed in UI)
      event_type: "SystemEvent"
    target:
      component_id: "ema_detector_instance_2"
      connector_id: "default_trigger"
      handler_method: "process"  # Default handler for system connectors
```

---

#### **2. Custom Event Connectors (Business Logic)**

**Purpose:** Domain-specific events (signals, alerts, custom triggers)

**Characteristics:**
- ✅ Event names **declared in manifest** (part of plugin contract)
- ✅ User **CANNOT rename** (breaking contract would break consumers)
- ✅ Maps to `Disposition.PUBLISH` in worker code
- ✅ Handler methods declared in manifest

**Manifest Declaration:**
```yaml
# plugins/signal_detectors/momentum_scout/manifest.yaml
plugin_id: "s1mple/momentum_scout/v1.0.0"
category: "signal_detector"

inputs:
  - connector_id: "default_trigger"  # Standard system input
    type: "system"
    required: true
  
  - connector_id: "context_ready"  # CUSTOM event input
    type: "custom_event"
    event_name: "CONTEXT_ASSESSMENT_READY"  # DECLARED (not generated!)
    handler_method: "on_context_ready"  # Custom handler
    required: false
    description: "Optional trigger when context aggregation completes"

outputs:
  - connector_id: "completion"  # Standard system output
    type: "system"
  
  - connector_id: "opportunity_detected"  # CUSTOM event output
    type: "custom_event"
    event_name: "MOMENTUM_OPPORTUNITY"  # DECLARED (not generated!)
    payload_type: "Signal"
    description: "Published when momentum conditions are met"
```

**UI Wiring:**
```typescript
// Strategy Builder UI
class WiringManager {
    wireCustomEvent(source: CustomConnector, target: CustomConnector): void {
        // Custom events: Use MANIFEST-DECLARED names (NOT generated!)
        addWiringRule({
            source: {
                component_id: source.workerId,
                connector_id: source.id,
                event_name: source.eventName,  // "MOMENTUM_OPPORTUNITY" from manifest
                event_type: "CustomEvent"
            },
            target: {
                component_id: target.workerId,
                connector_id: target.id,
                handler_method: target.handlerMethod  // "on_opportunity" from manifest
            }
        });
    }
}
```

**Generated Wiring:**
```yaml
# strategy_wiring_map.yaml
wiring_rules:
  - wiring_id: "momentum_to_planner"
    source:
      component_id: "momentum_scout_instance_1"
      connector_id: "opportunity_detected"
      event_name: "MOMENTUM_OPPORTUNITY"  # From manifest (immutable!)
      event_type: "CustomEvent"
    target:
      component_id: "momentum_planner_instance_1"
      connector_id: "opportunity_handler"
      handler_method: "on_opportunity"  # From manifest
```

---

#### **3. Data Connectors (DTO Output)**

**Purpose:** Make DTO production explicit in manifest (for documentation/UI)

**Characteristics:**
- ✅ Not wired via EventBus (uses TickCache instead)
- ✅ Declared for **explicitness** and **UI visualization**
- ✅ Enables UI to show data flow alongside event flow

**Manifest Declaration:**
```yaml
# plugins/context_workers/ema_detector/manifest.yaml
outputs:
  - connector_id: "completion"
    type: "system"
  
  - connector_id: "ema_data"  # Data connector (TickCache)
    type: "data"
    dto_class: "EMAOutputDTO"
    description: "EMA calculation result available in TickCache"
```

**NOT in wiring_map.yaml** (DTO dependencies handled via manifest `requires_dtos`):
```yaml
# Consumer manifest references DTO (not event!)
dependencies:
  requires_dtos:
    - source: "backend.dto_reg.s1mple.ema_detector.v1_0_0.ema_output_dto"
      dto_class: "EMAOutputDTO"
```

---

### **Worker Implementation (Bus-Agnostic)**

Workers remain **completely event-agnostic**:

```python
# plugins/signal_detectors/momentum_scout/worker.py
class MomentumScout(IWorker):
    """Event-aware worker - knows custom events, NOT EventBus."""
    
    def __init__(self, manifest: PluginManifest, params: MomentumParams):
        self._manifest = manifest
        self._params = params
    
    def process(self) -> DispositionEnvelope:
        """
        Standard handler (triggered via default_trigger connector).
        
        Worker is UNAWARE of:
        - EventBus existence
        - EventAdapter existence  
        - Actual event names used in wiring
        - Other workers in chain
        
        Worker KNOWS:
        - Custom event names FROM ITS OWN MANIFEST (part of its contract)
        - Handler method names FROM ITS OWN MANIFEST
        """
        # Business logic
        if self._detect_momentum():
            # Worker knows "MOMENTUM_OPPORTUNITY" (from its manifest)
            # But NOT that EventBus will route it!
            return DispositionEnvelope(
                disposition=Disposition.PUBLISH,
                event_name="MOMENTUM_OPPORTUNITY",  # From manifest
                event_payload=Signal(...)
            )
        
        return DispositionEnvelope(disposition=Disposition.CONTINUE)
    
    def on_context_ready(self, payload: dict) -> DispositionEnvelope:
        """
        Custom handler (triggered via context_ready connector).
        
        Declared in manifest.inputs[1].handler_method
        """
        # Alternative processing path
        return DispositionEnvelope(disposition=Disposition.CONTINUE)
```

---

### **Connector Abstraction Benefits**

#### **1. Explicitness**
All workers declare inputs/outputs in manifest → Self-documenting architecture

#### **2. UI Visualization**
Strategy Builder can render workers as boxes with connector sockets:
```
┌─────────────────────┐
│  EMA Detector       │
│                     │
│ IN:  [trigger]      │  ← System connector
│ OUT: [completion]   │  ← System connector
│ OUT: [ema_data]     │  ← Data connector
└─────────────────────┘

┌─────────────────────┐
│  Momentum Scout     │
│                     │
│ IN:  [trigger]      │  ← System connector
│ IN:  [context_rdy]  │  ← Custom event connector
│ OUT: [completion]   │  ← System connector
│ OUT: [opportunity]  │  ← Custom event connector
└─────────────────────┘
```

#### **3. Validation**
UI can validate connections:
- ✅ System → System (compatible)
- ✅ CustomEvent → CustomEvent (if event names match)
- ❌ System → CustomEvent (incompatible)
- ❌ Data → Event (incompatible)

#### **4. Flexibility**
- System event names: User can rename for readability
- Custom event names: Fixed by manifest (contract stability)
- Workers remain 100% event-agnostic

---

### **Complete Flow Example**

#### **Manifest (Momentum Scout)**
```yaml
plugin_id: "s1mple/momentum_scout/v1.0.0"

inputs:
  - connector_id: "default_trigger"
    type: "system"
    required: true
  
  - connector_id: "context_ready"
    type: "custom_event"
    event_name: "CONTEXT_ASSESSMENT_READY"
    handler_method: "on_context_ready"
    required: false

outputs:
  - connector_id: "completion"
    type: "system"
  
  - connector_id: "opportunity"
    type: "custom_event"
    event_name: "MOMENTUM_OPPORTUNITY"
    payload_type: "Signal"
```

#### **UI Wiring**
User drags connections in Strategy Builder:
1. `EMA_Detector.completion` → `MomentumScout.default_trigger` (system)
2. `ContextAggregator.context_ready` → `MomentumScout.context_ready` (custom event)
3. `MomentumScout.opportunity` → `StrategyPlanner.signal_input` (custom event)

#### **Generated strategy_wiring_map.yaml**
```yaml
wiring_rules:
  # System event (UI generated name)
  - wiring_id: "ema_to_momentum"
    source:
      component_id: "ema_detector_instance_1"
      connector_id: "completion"
      event_name: "_ema_detector_instance_1_completion"  # UI generated
      event_type: "SystemEvent"
    target:
      component_id: "momentum_scout_instance_1"
      connector_id: "default_trigger"
      handler_method: "process"
  
  # Custom event (manifest declared name)
  - wiring_id: "context_to_momentum"
    source:
      component_id: "context_aggregator_instance_1"
      connector_id: "context_ready"
      event_name: "CONTEXT_ASSESSMENT_READY"  # From manifest
      event_type: "CustomEvent"
    target:
      component_id: "momentum_scout_instance_1"
      connector_id: "context_ready"
      handler_method: "on_context_ready"  # From manifest
  
  # Custom event (manifest declared name)
  - wiring_id: "momentum_to_planner"
    source:
      component_id: "momentum_scout_instance_1"
      connector_id: "opportunity"
      event_name: "MOMENTUM_OPPORTUNITY"  # From manifest
      event_type: "CustomEvent"
    target:
      component_id: "strategy_planner_instance_1"
      connector_id: "signal_input"
      handler_method: "on_signal"
```

#### **Bootstrap (ConfigTranslator → EventWiringFactory)**
```python
# EventWiringFactory builds adapter configuration from wiring_map
adapters = factory.create_adapters(
    strategy_id="STRAT_001",
    workers={
        "ema_detector_instance_1": ema_worker,
        "momentum_scout_instance_1": momentum_worker,
        ...
    },
    wiring_spec=build_specs.wiring  # Contains all rules
)

# Each adapter configured with:
# - subscriptions: ["_ema_detector_instance_1_completion", "CONTEXT_ASSESSMENT_READY"]
# - handler_mapping: {
#     "_ema_detector_instance_1_completion": "process",
#     "CONTEXT_ASSESSMENT_READY": "on_context_ready"
#   }
# - system_event_publications: {"CONTINUE": "_momentum_scout_instance_1_completion"}
# - allowed_publications: {"MOMENTUM_OPPORTUNITY"}
```

#### **Runtime**
```python
# EventAdapter receives "_ema_detector_instance_1_completion" event
# Calls momentum_worker.process()
# Worker returns DispositionEnvelope(PUBLISH, "MOMENTUM_OPPORTUNITY", signal)
# EventAdapter validates "MOMENTUM_OPPORTUNITY" in allowed_publications
# EventAdapter publishes to EventBus
# strategy_planner's EventAdapter receives event
# Calls planner.on_signal(signal)
```

---

### **Architectural Principles**

1. **Workers are connector-based factories**
   - Input connectors = triggers
   - Output connectors = products
   - Zero knowledge of wiring/EventBus

2. **UI is the wiring authority**
   - System events: UI generates (deterministic) OR user renames
   - Custom events: UI uses manifest declarations
   - Wiring stored in `strategy_wiring_map.yaml` (static)

3. **Event names decided at configuration time**
   - NO runtime generation
   - ALL names in `strategy_wiring_map.yaml` before bootstrap
   - ConfigTranslator → BuildSpecs → EventWiringFactory → EventAdapters

4. **Connector types have different semantics**
   - System: Generated/renamable (flow control)
   - Custom: Declared/immutable (business logic)
   - Data: Explicit DTO flow (visualization only)

---

### **Event-Centric Wiring Model (Refined)**

**Critical Insight:** Wiring rules configure **individual EventAdapters**, NOT worker-to-worker connections.

**Incorrect Mental Model (Connection-Based):**
```yaml
# ❌ This suggests direct worker-to-worker connections
wiring_rules:
  - source: worker_a.output_connector
    target: worker_b.input_connector
```

**Correct Mental Model (Event-Centric, Adapter-Based):**
```yaml
# ✅ Each rule configures ONE adapter's subscriptions/publications
adapter_configurations:
  worker_a_adapter:
    publications:
      - connector_id: "completion"
        event_name: "WORKER_A_DONE"
        scope: "strategy"
  
  worker_b_adapter:
    subscriptions:
      - event_name: "WORKER_A_DONE"
        connector_id: "default_trigger"
        handler_method: "process"
```

**Key Distinction:**
- **Event names are the interface** (not worker references)
- **Adapters don't know sources or targets** (loose coupling)
- **EventBus routes events by name** (workers remain decoupled)

**Why This Matters:**
```python
# worker_b_adapter receives "WORKER_A_DONE" event
# Adapter does NOT know:
# - Which worker published it (worker_a? worker_x? platform singleton?)
# - Why it was published
# - Who else subscribed to it

# Adapter ONLY knows:
# - Event name matched subscription: "WORKER_A_DONE"
# - Which connector to trigger: "default_trigger"
# - Which handler to call: worker_b.process()
```

**Architecture Benefit:**
- Worker A can be replaced without touching worker B
- Multiple workers can publish same event name
- Multiple workers can subscribe to same event name
- Platform components and strategy workers use identical pattern

---

### **Uniform EventAdapter Pattern**

**Principle:** ALL components use the SAME EventAdapter, WITHOUT special cases.

**Components Using EventAdapter:**
- ✅ Strategy workers (SignalDetectors, ContextWorkers, etc.)
- ✅ Platform singletons (PositionManager, OrderRouter, etc.)
- ✅ FlowInitiators (per-strategy tick entry points)
- ✅ Any future component types

**NO Platform vs Strategy Distinction in EventAdapter:**
```python
# ❌ WRONG - Platform adapter with special logic
class PlatformEventAdapter(EventAdapter):
    def _publish_event(self, event_name: str, payload: Any):
        # Special platform logic here...
        self.bus.publish(event_name, ScopeLevel.PLATFORM, payload)

# ✅ CORRECT - Uniform adapter for ALL components
class EventAdapter:
    def __init__(self, component: IWorker, bus: EventBus, config: AdapterConfig):
        self._component = component
        self._bus = bus
        self._config = config  # Contains scope info
    
    def _publish_event(self, connector_id: str, payload: Any):
        # Scope determined by configuration, not adapter type
        publication = self._config.get_publication(connector_id)
        self._bus.publish(
            publication.event_name,
            publication.scope,  # PLATFORM or STRATEGY from config
            payload
        )
```

**How Platform/Strategy Separation Works:**
```yaml
# Platform singleton adapter config
adapter_configurations:
  position_manager_adapter:
    strategy_id: null  # ← Platform scope indicator
    publications:
      - connector_id: "position_updated"
        event_name: "POSITION_UPDATED"
        scope: "platform"  # ← EventBus will broadcast to ALL strategies

# Strategy worker adapter config
adapter_configurations:
  signal_detector_adapter:
    strategy_id: "STRAT_001"  # ← Strategy scope indicator
    publications:
      - connector_id: "signal_detected"
        event_name: "MOMENTUM_SIGNAL"
        scope: "strategy"  # ← EventBus will filter to STRAT_001 only
```

**EventBus Filtering (Automatic):**
```python
# EventBus implementation (simplified)
class EventBus:
    def publish(self, event_name: str, scope: ScopeLevel, payload: Any, strategy_id: str = None):
        if scope == ScopeLevel.PLATFORM:
            # Broadcast to all strategy scopes + platform subscribers
            self._publish_to_all_scopes(event_name, payload)
        elif scope == ScopeLevel.STRATEGY:
            # Publish only to specified strategy scope
            self._publish_to_strategy(event_name, payload, strategy_id)
    
    def subscribe(self, event_name: str, handler: Callable, strategy_id: str = None):
        # Subscribe to events in specific strategy scope
        # Platform components subscribe with strategy_id=None
        # Strategy components subscribe with their strategy_id
```

**Result:**
- EventAdapter code is IDENTICAL for platform and strategy components
- Scope filtering happens in EventBus (not adapter)
- Configuration determines behavior (not code)

---

### **Bootstrap Validation Strategy**

**Principle:** Fail-fast during bootstrap, trust configuration at runtime.

**Validation Timing:**
```
Configuration Load → Bootstrap Validation → Runtime (No Validation)
                           ↑
                    (Fail-fast here!)
```

**What Gets Validated at Bootstrap:**
1. **Connector existence** - Do declared connectors exist in manifest?
2. **Event name matching** - Do custom event connectors match across workers?
3. **Handler methods** - Do target workers have declared handler methods?
4. **Payload types** - Do source/target payload types match?
5. **Dependency completeness** - Are all required DTOs available?
6. **Scope validity** - Are scope declarations (PLATFORM/STRATEGY) valid?

**Bootstrap Validation Example:**
```python
# EventWiringFactory.create_adapters() - Runs ONCE at bootstrap
class EventWiringFactory:
    def create_adapters(
        self,
        strategy_id: str,
        workers: Dict[str, IWorker],
        wiring_spec: WiringSpec
    ) -> Dict[str, EventAdapter]:
        
        for rule in wiring_spec.adapter_configurations:
            # ✅ Validate connector exists in manifest
            if not self._connector_exists(rule.connector_id, worker.manifest):
                raise ConfigurationError(f"Connector {rule.connector_id} not in manifest")
            
            # ✅ Validate handler method exists
            if not hasattr(worker, rule.handler_method):
                raise ConfigurationError(f"Handler {rule.handler_method} not found")
            
            # ✅ Validate payload type compatibility
            if not self._payload_types_match(source_type, target_type):
                raise ConfigurationError(f"Payload type mismatch: {source_type} vs {target_type}")
        
        # If we reach here: Configuration is VALID
        return adapters
```

**What Does NOT Get Validated at Runtime:**
```python
# EventAdapter.handle_event() - Runs MANY times per second
class EventAdapter:
    def handle_event(self, event: Event):
        # ❌ NO validation here (performance critical!)
        # Trust that bootstrap validated everything
        
        subscription = self._config.get_subscription(event.name)
        handler = getattr(self._component, subscription.handler_method)
        result = handler(event.payload)
        
        # ❌ NO payload type checks
        # ❌ NO connector existence checks
        # ❌ NO event name validation
        # Trust bootstrap validation!
```

**Performance Impact:**
- Bootstrap: ~100ms one-time validation cost
- Runtime: ZERO validation overhead (thousands of events/second)
- Result: Fail-fast safety without performance penalty

---

### **Payload Type Declaration in Manifest**

**Problem Solved:** How does adapter know which payload type to expect/produce?

**Solution:** Declare payload types explicitly in manifest inputs/outputs.

**Enhanced Manifest Schema:**
```yaml
# plugins/signal_detectors/momentum_scout/manifest.yaml
plugin_id: "s1mple/momentum_scout/v1.0.0"

inputs:
  - connector_id: "default_trigger"
    type: "system"
    required: true
    payload_type: null  # System connectors typically no payload
  
  - connector_id: "context_ready"
    type: "custom_event"
    event_name: "CONTEXT_ASSESSMENT_READY"
    handler_method: "on_context_ready"
    payload_type: "ContextAssessment"  # ← Declares expected type
    payload_source: "backend.dtos.strategy.context_assessment.ContextAssessment"
    required: false

outputs:
  - connector_id: "completion"
    type: "system"
    payload_type: null
  
  - connector_id: "signal_detected"
    type: "custom_event"
    event_name: "MOMENTUM_SIGNAL"
    payload_type: "Signal"  # ← Declares produced type
    payload_source: "backend.dtos.strategy.signal.Signal"
```

**Bootstrap Validation Uses This:**
```python
# EventWiringFactory validates type compatibility
class EventWiringFactory:
    def _validate_payload_compatibility(
        self,
        source_connector: ConnectorSpec,
        target_connector: ConnectorSpec
    ):
        if source_connector.payload_type != target_connector.payload_type:
            raise ConfigurationError(
                f"Payload type mismatch: "
                f"{source_connector.connector_id} produces {source_connector.payload_type}, "
                f"{target_connector.connector_id} expects {target_connector.payload_type}"
            )
        
        # Also validate source can be imported
        try:
            import_class(source_connector.payload_source)
        except ImportError as e:
            raise ConfigurationError(f"Cannot import {source_connector.payload_source}: {e}")
```

**Adapter Uses This at Runtime:**
```python
# EventAdapter knows what to expect (no runtime checks needed!)
class EventAdapter:
    def __init__(self, component: IWorker, config: AdapterConfig):
        self._subscriptions = {
            "CONTEXT_ASSESSMENT_READY": SubscriptionInfo(
                connector_id="context_ready",
                handler_method="on_context_ready",
                payload_type=ContextAssessment  # ← Known at bootstrap
            )
        }
    
    def handle_event(self, event: Event):
        sub = self._subscriptions[event.name]
        # No type check needed - bootstrap validated this!
        handler = getattr(self._component, sub.handler_method)
        handler(event.payload)  # Trust it's correct type
```

---

### **System DTOs vs TickCache DTOs (Clarified)**

**Two Separate Transport Mechanisms:**

#### **1. System DTOs (Transported via Events)**

**Purpose:** Flow control signals (Signal, Risk, StrategyDirective, etc.)

**Transport:** EventBus with DispositionEnvelope
```python
# SignalDetector publishes Signal via event
return DispositionEnvelope(
    disposition=Disposition.PUBLISH,
    event_name="MOMENTUM_SIGNAL",
    event_payload=Signal(confidence=0.85, ...)  # ← In event payload
)

# EventAdapter publishes to EventBus
self._bus.publish(
    "MOMENTUM_SIGNAL",
    scope=ScopeLevel.STRATEGY,
    payload=envelope.event_payload  # ← Signal travels in event
)

# StrategyPlanner receives via event
def on_signal(self, signal: Signal):
    # Signal came from event payload
    self.plan_entry(signal)
```

**Manifest Declaration:**
```yaml
outputs:
  - connector_id: "signal_detected"
    type: "custom_event"
    payload_type: "Signal"  # ← Declares event payload type
    payload_source: "backend.dtos.strategy.signal.Signal"
```

#### **2. TickCache DTOs (Transported via StrategyCache)**

**Purpose:** Worker calculation results (EMAOutputDTO, MarketStructureDTO, etc.)

**Transport:** StrategyCache.set_result_dto() / get_required_dtos()
```python
# EMADetector stores result in TickCache
result = EMAOutputDTO(fast=50.2, slow=51.1, ...)
self.strategy_cache.set_result_dto(result)

return DispositionEnvelope(
    disposition=Disposition.CONTINUE
    # ← NO event_payload! Result is in TickCache
)

# Consumer retrieves from TickCache
class MomentumScout:
    def process(self):
        # Get DTO from cache
        ema_data = self.strategy_cache.get_required_dtos()[EMAOutputDTO]
        
        # Use in calculation
        if ema_data.fast > ema_data.slow:
            return self._publish_signal()
```

**Manifest Declaration:**
```yaml
# Producer manifest
dependencies:
  produces_dtos:
    - source: "backend.dto_reg.s1mple.ema_detector.v1_0_0.ema_output_dto"
      dto_class: "EMAOutputDTO"

# Consumer manifest
dependencies:
  requires_dtos:
    - source: "backend.dto_reg.s1mple.ema_detector.v1_0_0.ema_output_dto"
      dto_class: "EMAOutputDTO"
```

**Key Difference:**
- **System DTOs:** Event-driven triggers (Signal → Plan → Execute)
- **TickCache DTOs:** Dependency resolution (EMA data available for MomentumScout)

---

### **Complete Architecture Flow Example**

**Scenario:** EMADetector → MomentumScout → StrategyPlanner

#### **1. Manifests**

```yaml
# plugins/context_workers/ema_detector/manifest.yaml
outputs:
  - connector_id: "completion"
    type: "system"
    payload_type: null
  - connector_id: "ema_data"
    type: "data"
    dto_class: "EMAOutputDTO"

dependencies:
  produces_dtos:
    - source: "backend.dto_reg.s1mple.ema_detector.v1_0_0.ema_output_dto"
      dto_class: "EMAOutputDTO"
```

```yaml
# plugins/signal_detectors/momentum_scout/manifest.yaml
inputs:
  - connector_id: "default_trigger"
    type: "system"
    payload_type: null

outputs:
  - connector_id: "signal_detected"
    type: "custom_event"
    event_name: "MOMENTUM_SIGNAL"
    payload_type: "Signal"
    payload_source: "backend.dtos.strategy.signal.Signal"

dependencies:
  requires_dtos:
    - source: "backend.dto_reg.s1mple.ema_detector.v1_0_0.ema_output_dto"
      dto_class: "EMAOutputDTO"
```

```yaml
# plugins/strategy_workers/strategy_planner/manifest.yaml
inputs:
  - connector_id: "signal_input"
    type: "custom_event"
    event_name: "MOMENTUM_SIGNAL"
    handler_method: "on_signal"
    payload_type: "Signal"
    payload_source: "backend.dtos.strategy.signal.Signal"
```

#### **2. Wiring Map (Event-Centric)**

```yaml
# strategy_wiring_map.yaml
adapter_configurations:
  ema_detector_adapter:
    strategy_id: "STRAT_001"
    publications:
      - connector_id: "completion"
        event_name: "_EMA_READY"
        scope: "strategy"
  
  momentum_scout_adapter:
    strategy_id: "STRAT_001"
    subscriptions:
      - event_name: "_EMA_READY"
        connector_id: "default_trigger"
        handler_method: "process"
    publications:
      - connector_id: "signal_detected"
        event_name: "MOMENTUM_SIGNAL"
        scope: "strategy"
  
  strategy_planner_adapter:
    strategy_id: "STRAT_001"
    subscriptions:
      - event_name: "MOMENTUM_SIGNAL"
        connector_id: "signal_input"
        handler_method: "on_signal"
```

#### **3. Bootstrap Validation**

```python
# EventWiringFactory.create_adapters()
# ✅ Validates:
# - "completion" connector exists in ema_detector manifest
# - "default_trigger" connector exists in momentum_scout manifest
# - "process" method exists on MomentumScout worker
# - "signal_detected" connector exists in momentum_scout manifest
# - "MOMENTUM_SIGNAL" payload types match (Signal → Signal)
# - "on_signal" method exists on StrategyPlanner worker
# - EMAOutputDTO dependency available (requires_dtos satisfied)

# If ANY validation fails → ConfigurationError (fail-fast!)
# If ALL validations pass → Create adapters (trust at runtime)
```

#### **4. Runtime Execution**

```python
# Step 1: EMADetector processes
ema_detector.process()
# - Calculates EMA
# - Stores to TickCache: strategy_cache.set_result_dto(EMAOutputDTO(...))
# - Returns DispositionEnvelope(CONTINUE)
# - EventAdapter publishes "_EMA_READY" event (no payload)

# Step 2: EventBus routes "_EMA_READY" → momentum_scout_adapter
momentum_scout_adapter.handle_event(Event("_EMA_READY", None))
# - Looks up subscription: "_EMA_READY" → connector "default_trigger"
# - Calls momentum_scout.process()

# Step 3: MomentumScout processes
momentum_scout.process()
# - Retrieves EMAOutputDTO from TickCache
# - Detects momentum condition
# - Returns DispositionEnvelope(PUBLISH, "MOMENTUM_SIGNAL", Signal(...))
# - EventAdapter publishes "MOMENTUM_SIGNAL" event with Signal payload

# Step 4: EventBus routes "MOMENTUM_SIGNAL" → strategy_planner_adapter
strategy_planner_adapter.handle_event(Event("MOMENTUM_SIGNAL", Signal(...)))
# - Looks up subscription: "MOMENTUM_SIGNAL" → connector "signal_input"
# - Calls strategy_planner.on_signal(Signal(...))

# Step 5: StrategyPlanner processes
strategy_planner.on_signal(signal: Signal)
# - Receives Signal from event payload
# - Creates EntryPlan
# - Returns DispositionEnvelope(PUBLISH, "ENTRY_PLAN_READY", EntryPlan(...))
```

---

**Decision:** ✅ **APPROVED - Unified Event-Centric Connector Architecture**

**Impact:**
- ⚠️ PLUGIN_ANATOMY.md - Add payload_type, payload_source fields to connector schema
- ⚠️ EVENT_DRIVEN_WIRING.md - Document event-centric wiring model (not connection-based)
- ⚠️ ConfigTranslator - Parse adapter_configurations from wiring_map
- ⚠️ EventWiringFactory - Implement bootstrap validation (fail-fast)
- ⚠️ EventAdapter - Remove any platform vs strategy distinctions (uniform implementation)
- ⚠️ AdapterConfig - Store scope (PLATFORM/STRATEGY) from wiring_map
- ⚠️ EventBus - Ensure scope filtering works correctly
- ⚠️ Strategy Builder UI - Generate event-centric wiring (not connection-based)
- ✅ Workers remain 100% event-agnostic (no changes needed)

---

### GAP-003: PUBLISH Disposition - Payload Location Ambiguity

**Location:** `EVENT_DRIVEN_WIRING.md`, `WORKER_TAXONOMY.md`

**Problem:**
Documentation contradicts itself on where PUBLISH payload goes:

**EVENT_DRIVEN_WIRING.md says (V2 pattern):**
```python
return DispositionEnvelope(
    disposition="PUBLISH",
    event_name="BREAKOUT_SIGNAL",
    event_payload=Signal(...)  # ❌ "Payload goes to TickCache, not event!"
)

# Note: This is a V2 pattern. V3 may include system DTOs in event payloads
```

**WORKER_TAXONOMY.md says:**
```python
# SignalDetector Output Pattern
DispositionEnvelope(PUBLISH) with Signal (system DTO)
```

**DispositionEnvelope DTO has:**
```python
class DispositionEnvelope(BaseModel):
    disposition: Literal["CONTINUE", "PUBLISH", "STOP"]
    event_payload: Optional[BaseModel] = None  # ← Field exists!
```

**Conflict:**
- If payload goes to TickCache (V2), why does DispositionEnvelope have `event_payload`?
- If payload goes in event (V3), why does doc say "V2 pattern"?
- **No clear V3 specification!**

**Scenario that fails:**
```python
# SignalDetector publishes
return DispositionEnvelope(
    disposition="PUBLISH",
    event_payload=Signal(confidence=0.85, ...)
)

# EventAdapter receives this - what does it do?
# Option A: Store to TickCache, publish notification-only event
cache.set_result_dto(worker, envelope.event_payload)
bus.publish("SIGNAL_DETECTED", payload=None)

# Option B: Publish payload directly in event
bus.publish("SIGNAL_DETECTED", payload=envelope.event_payload)

# Option C: Both (duplication!)
cache.set_result_dto(worker, envelope.event_payload)
bus.publish("SIGNAL_DETECTED", payload=envelope.event_payload)
```

**Consumer impact:**
```python
# If Option A: Consumer must read TickCache
def on_signal(event):
    signal = self.strategy_cache.get_result_dto(Signal)  # From cache
    process(signal)

# If Option B: Consumer reads event payload
def on_signal(event):
    signal = event['payload']  # From event directly
    process(signal)
```

**Design Question:**
Where should PUBLISH disposition payload go - TickCache, EventBus, or both?

**Proposed Solutions:**

**Option A: TickCache Only (V2 Pattern)**
```python
# Worker returns envelope
return DispositionEnvelope(
    disposition="PUBLISH",
    event_name="SIGNAL_DETECTED",
    event_payload=Signal(...)  # Stored to cache, NOT in event
)

# EventAdapter behavior
cache.set_result_dto(worker, envelope.event_payload)  # ✅ Store
bus.publish(envelope.event_name, payload=None)  # ✅ Notify only
```

**Pros:**
- ✅ Consistent with TickCache pattern (all DTOs in cache)
- ✅ Single source of truth (cache)

**Cons:**
- ⚠️ Consumers must access TickCache (coupling to cache)
- ⚠️ Async consumers can't get payload if TickCache cleared
- ⚠️ DispositionEnvelope.event_payload field is misleading

**Option B: EventBus Payload (V3 Simplified)**
```python
# Worker returns envelope
return DispositionEnvelope(
    disposition="PUBLISH",
    event_name="SIGNAL_DETECTED",
    event_payload=Signal(...)  # Goes directly in event
)

# EventAdapter behavior
bus.publish(envelope.event_name, payload=envelope.event_payload)  # ✅ Direct
# NOT stored to TickCache (signals are ephemeral)
```

**Pros:**
- ✅ Simple for consumers (payload in event)
- ✅ Async-friendly (subscribers get payload immediately)
- ✅ DispositionEnvelope.event_payload field makes sense

**Cons:**
- ⚠️ Signals not in TickCache (inconsistent with context DTOs)
- ⚠️ Can't query TickCache for "what signals were published this tick?"

**Option C: Dual Write (Both)**
```python
# EventAdapter behavior
cache.set_result_dto(worker, envelope.event_payload)  # ✅ Persistence
bus.publish(envelope.event_name, payload=envelope.event_payload)  # ✅ Delivery
```

**Pros:**
- ✅ Best of both (cache persistence + event delivery)
- ✅ Flexible consumption (read from cache OR event)

**Cons:**
- ⚠️ Duplication (same data in two places)
- ⚠️ Sync overhead (two writes per publish)

**Decision Needed:**
- [ ] Option A: TickCache only (V2 pattern)
- [ ] Option B: EventBus payload (V3 simplified)
- [ ] Option C: Dual write (both cache and event)
- [ ] Other: _______________

**Impact:**
- EventAdapter implementation
- Consumer (StrategyPlanner, PlanningAggregator) implementation
- DispositionEnvelope semantics
- WORKER_TAXONOMY.md, EVENT_DRIVEN_WIRING.md rewrite

---

### GAP-004: EventAdapter Ownership & Creation Flow

**Location:** `EVENT_DRIVEN_WIRING.md`, `LAYERED_ARCHITECTURE.md`

**Problem:**
Unclear **who creates and owns EventAdapter instances**:

**EVENT_DRIVEN_WIRING.md says:**
```python
adapter_config = {
    'component_ref': worker_instance,  # ← Needs worker instance
    'eventbus_ref': eventbus,
    'subscriptions': [...]
}
```

**LAYERED_ARCHITECTURE.md says:**
```
EventWiringFactory - Wires EventAdapters to EventBus
```

**But:**
- WorkerFactory creates workers
- EventWiringFactory creates adapters
- **How does EventWiringFactory get worker references?**

**Problematic flow:**
```python
# Step 1: WorkerFactory creates workers
workers = WorkerFactory.build_all(workforce_spec)
# workers = [worker1, worker2, worker3]

# Step 2: EventWiringFactory creates adapters
# ❌ How does it get worker references from Step 1?
adapters = EventWiringFactory.create_adapters(wiring_spec)
# Needs worker references but WorkerFactory is done!
```

**Design Question:**
Who creates EventAdapters, who owns them, and what's the creation order?

**Proposed Solutions:**

**Option A: StrategyFactory Coordinates Both**
```python
class StrategyFactory:
    def build_strategy(self, strategy_spec: StrategyBuildSpec):
        # 1. Create workers
        workers = self.worker_factory.build_all(strategy_spec.workforce)
        
        # 2. Create adapters WITH worker references
        adapters = self.wiring_factory.create_adapters(
            wiring_spec=strategy_spec.wiring,
            worker_registry=workers  # ✅ Pass references
        )
        
        # 3. Wire adapters to EventBus
        for adapter in adapters:
            adapter.wire()
        
        return Strategy(workers=workers, adapters=adapters)
```

**Pros:**
- ✅ Clear coordination (one factory orchestrates)
- ✅ Worker references passed explicitly

**Cons:**
- ⚠️ StrategyFactory has more responsibility (orchestration)
- ⚠️ Need Strategy container object to return

**Option B: WorkerFactory Creates Adapters Too**
```python
class WorkerFactory:
    def build_worker(self, spec: WorkerBuildSpec) -> Tuple[Worker, EventAdapter]:
        # 1. Create worker
        worker = self._instantiate_worker(spec)
        
        # 2. Create adapter for this worker
        adapter = EventAdapter(
            component=worker,
            eventbus=self._eventbus
        )
        
        return worker, adapter
```

**Pros:**
- ✅ One factory, one responsibility (worker + adapter are paired)
- ✅ No coordination needed

**Cons:**
- ⚠️ WorkerFactory needs wiring knowledge (SRP violation?)
- ⚠️ Wiring configuration split between workforce and wiring specs

**Option C: Workers Self-Wrap with Adapters**
```python
class StandardWorker:
    def __init__(self, spec: WorkerBuildSpec):
        # Worker creates its own adapter
        self._adapter = EventAdapter(component=self, eventbus=spec.eventbus)
        self._adapter.wire(spec.subscriptions)
```

**Pros:**
- ✅ Simple (no factory coordination)
- ✅ Worker owns lifecycle

**Cons:**
- ⚠️ Workers are NO LONGER bus-agnostic (architectural violation!)
- ⚠️ Workers must know EventBus (coupling)

**Decision Needed:**
- [ ] Option A: StrategyFactory coordinates (workers + adapters)
- [ ] Option B: WorkerFactory creates both
- [ ] Option C: Workers self-wrap (violates bus-agnostic principle)
- [ ] Other: _______________

**Impact:**
- Factory hierarchy (WorkerFactory, EventWiringFactory, StrategyFactory)
- Worker initialization flow
- Bootstrap sequence
- LAYERED_ARCHITECTURE.md bootstrap section rewrite

---

## 🟡 MEDIUM GAPS (Inconsistencies to Resolve)

### GAP-005: ContextWorker Objective Data - No Enforcement

**Location:** `OBJECTIVE_DATA_PHILOSOPHY.md`, `WORKER_TAXONOMY.md`

**Problem:**
ContextWorkers must produce objective facts and NEVER publish to EventBus, but **nothing enforces this**:

**Philosophy says:**
```
ContextWorker Output Pattern:
- Stores plugin-specific DTOs to TickCache via set_result_dto()
- NEVER publishes events to EventBus
```

**Reality:**
```python
class MaliciousContextWorker(StandardWorker):
    def process(self) -> DispositionEnvelope:
        # ❌ I'm a ContextWorker but I break the rules
        return DispositionEnvelope(
            disposition="PUBLISH",  # Allowed!
            event_payload=Signal(...)
        )
        # No runtime error - platform doesn't check!
```

**Design Question:**
Should architectural constraints be enforced in code, or is documentation sufficient?

**Proposed Solutions:**

**Option A: Type-Safe Base Classes**
```python
class BaseContextWorker(ABC):
    @abstractmethod
    def process(self) -> Literal["CONTINUE"]:
        """Context workers can ONLY return CONTINUE."""
        ...

class EMADetector(BaseContextWorker):
    def process(self) -> Literal["CONTINUE"]:
        self.strategy_cache.set_result_dto(self, dto)
        return "CONTINUE"  # ✅ Type system enforces
    
    # def process(self) -> DispositionEnvelope:
    #     return DispositionEnvelope(disposition="PUBLISH")
    # ❌ Type error - return type mismatch!
```

**Pros:**
- ✅ Compile-time enforcement (Pylance catches violations)
- ✅ Clear contract (type signature enforces behavior)

**Cons:**
- ⚠️ More base class complexity
- ⚠️ DispositionEnvelope not used by ContextWorkers (different pattern)

**Option B: EventAdapter Validation**
```python
class EventAdapter:
    def _interpret_disposition(self, envelope: DispositionEnvelope):
        # Check manifest type
        if self.worker_manifest.type == "context_worker":
            if envelope.disposition == "PUBLISH":
                raise ArchitecturalViolation(
                    "ContextWorkers cannot PUBLISH to EventBus"
                )
```

**Pros:**
- ✅ Runtime enforcement (catches violations)
- ✅ DispositionEnvelope pattern preserved

**Cons:**
- ⚠️ Runtime error (not caught at compile time)
- ⚠️ Fails late (during execution, not bootstrap)

**Option C: Bootstrap Validation**
```python
class DependencyValidator:
    def validate_workforce(self, workforce_spec: WorkforceSpec):
        for worker_spec in workforce_spec.workers:
            if worker_spec.manifest.type == "context_worker":
                # Check wiring spec
                if self._worker_publishes_events(worker_spec):
                    raise ConfigurationError(
                        f"ContextWorker {worker_spec.name} "
                        "configured to publish events (architectural violation)"
                    )
```

**Pros:**
- ✅ Fail-fast (bootstrap catches violations)
- ✅ Prevents deployment of broken configurations

**Cons:**
- ⚠️ Requires wiring spec inspection (complex validation)
- ⚠️ Can't catch violations in worker code (only config)

**Option D: Documentation Only (Current)**
```
Trust developers to follow documented conventions.
No code enforcement.
```

**Pros:**
- ✅ Simple (no enforcement code)
- ✅ Flexible (power users can break rules if needed)

**Cons:**
- ⚠️ Easy to violate accidentally
- ⚠️ No safety net

**Decision Needed:**
- [ ] Option A: Type-safe base classes (compile-time)
- [ ] Option B: EventAdapter validation (runtime)
- [ ] Option C: Bootstrap validation (fail-fast)
- [ ] Option D: Documentation only (no enforcement)
- [ ] Other: _______________

**Impact:**
- BaseWorker class hierarchy
- EventAdapter implementation
- DependencyValidator scope
- Developer experience (friction vs safety)

---

### GAP-006: PlanningAggregator Architectural Position

**Location:** `WORKER_TAXONOMY.md`, `PLATFORM_COMPONENTS.md`

**Problem:**
PlanningAggregator is mentioned as "platform component (NOT worker)" but:
- NOT listed in PLATFORM_COMPONENTS.md
- NOT listed in LAYERED_ARCHITECTURE.md singletons
- No specification of lifecycle, ownership, or creation

**Questions:**
1. Is PlanningAggregator a **singleton** or **per-strategy instance**?
2. Who creates it? (StrategyFactory? Platform bootstrap?)
3. Where does it live? (`backend/core/`? `backend/aggregators/`?)
4. Does it have an EventAdapter? (If it subscribes to events, it needs one)
5. Is it a worker in disguise? (It processes events, produces output)

**Design Question:**
What IS PlanningAggregator architecturally?

**Proposed Solutions:**

**Option A: Platform Singleton Component**
```python
# backend/core/planning_aggregator.py
class PlanningAggregator:
    """Singleton platform component (like EventBus, StrategyCache)."""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def aggregate_plans(
        self,
        entry: EntryPlan,
        size: SizePlan,
        exit: ExitPlan,
        execution: ExecutionPlan
    ) -> ExecutionDirective:
        """Combine 4 plans into ExecutionDirective."""
        ...
```

**Pros:**
- ✅ Consistent with other platform components
- ✅ Shared across all strategies

**Cons:**
- ⚠️ Multi-strategy concurrency (same singleton issue as StrategyCache)
- ⚠️ How to isolate plans per strategy?

**Option B: Per-Strategy Component (Not Singleton)**
```python
# Created by StrategyFactory
class PlanningAggregator:
    def __init__(self, strategy_id: str):
        self._strategy_id = strategy_id
        self._pending_plans = {}
```

**Pros:**
- ✅ Natural strategy isolation
- ✅ Clear ownership (strategy owns its aggregator)

**Cons:**
- ⚠️ Not a "platform component" (per-strategy instance)
- ⚠️ Must be managed by StrategyFactory

**Option C: It's Actually a Worker**
```python
# Rename to PlanningAggregatorWorker
class PlanningAggregatorWorker(StandardWorker):
    """
    Special worker type: planning_aggregator
    Subscribes to plan events, publishes ExecutionDirective
    """
    manifest.type = "planning_aggregator"
```

**Pros:**
- ✅ Consistent with worker pattern (subscribes, processes, publishes)
- ✅ WorkerFactory handles creation
- ✅ EventAdapter handles wiring

**Cons:**
- ⚠️ Philosophy says "platform component, NOT worker"
- ⚠️ Mandatory for all strategies (not optional plugin)

**Decision Needed:**
- [ ] Option A: Platform singleton
- [ ] Option B: Per-strategy component
- [ ] Option C: Special worker type
- [ ] Other: _______________

**Impact:**
- PLATFORM_COMPONENTS.md update
- Factory responsibilities
- Worker taxonomy (if Option C)
- Wiring configuration

---

### GAP-007: ExecutionDirective Causality ID Duplication

**Location:** `backend/dtos/execution/execution_directive.py`, `backend/dtos/causality.py`

**Problem:**
ExecutionDirective has ID in **two places**:

```python
class ExecutionDirective(BaseModel):
    execution_directive_id: str = Field(default_factory=generate_execution_directive_id)
    causality: CausalityChain  # Also contains execution_directive_id!

class CausalityChain(BaseModel):
    execution_directive_id: str | None = None
```

**Scenario:**
```python
directive = ExecutionDirective(
    execution_directive_id="EXD_123",  # Field 1
    causality=CausalityChain(
        execution_directive_id="EXD_456"  # Field 2 - DIFFERENT!
    )
)
# Which ID is canonical?
```

**Design Question:**
Should IDs live in parent DTO or in causality chain?

**Proposed Solutions:**

**Option A: ID in Causality Only**
```python
class ExecutionDirective(BaseModel):
    # No execution_directive_id field
    causality: CausalityChain  # Contains ID

# Access via causality
directive.causality.execution_directive_id
```

**Pros:**
- ✅ Single source of truth (causality chain)
- ✅ Consistent (all IDs in causality)

**Cons:**
- ⚠️ Verbose access (need to go through causality)
- ⚠️ Causality chain semantics unclear (is it metadata or just ID container?)

**Option B: ID in Parent Only**
```python
class ExecutionDirective(BaseModel):
    execution_directive_id: str = Field(default_factory=...)
    causality: CausalityChain  # NO execution_directive_id

class CausalityChain(BaseModel):
    # execution_directive_id field removed
    tick_id: str
    signal_ids: list[str]
    # Only upstream IDs, not own ID
```

**Pros:**
- ✅ Intuitive access (directive.execution_directive_id)
- ✅ Causality chain is pure lineage (no self-reference)

**Cons:**
- ⚠️ Inconsistent with other DTOs (Signal has ID in both places?)
- ⚠️ Must build causality chain with directive ID separately

**Option C: Validation to Enforce Consistency**
```python
class ExecutionDirective(BaseModel):
    execution_directive_id: str
    causality: CausalityChain
    
    @model_validator(mode='after')
    def validate_causality_consistency(self) -> 'ExecutionDirective':
        if self.causality.execution_directive_id != self.execution_directive_id:
            raise ValueError("Causality chain ID must match directive ID")
        return self
```

**Pros:**
- ✅ Prevents inconsistency
- ✅ Both fields exist (backward compatible)

**Cons:**
- ⚠️ Duplication still exists (just validated)
- ⚠️ Must set ID in two places (boilerplate)

**Decision Needed:**
- [ ] Option A: Causality only (remove from parent)
- [ ] Option B: Parent only (remove from causality)
- [ ] Option C: Both with validation
- [ ] Other: _______________

**Impact:**
- ExecutionDirective, Signal, Risk DTO structure
- CausalityChain semantics
- DTO creation boilerplate

---

### GAP-008: Multi-Strategy Concurrent Execution Design Missing

**Location:** `LAYERED_ARCHITECTURE.md` (ParallelRunService mentioned)

**Problem:**
ParallelRunService is listed as Service Layer component for "parallel strategy execution", but:
- StrategyCache is singleton (GAP-001)
- EventBus is N-to-N broadcast (no strategy namespacing)
- TickCacheManager design missing
- No isolation mechanism specified

**Design Question:**
How do multiple strategies run concurrently without interfering?

**Required Decisions:**
1. **Strategy Isolation:** Separate cache instances or multi-tenant singleton?
2. **Event Namespacing:** Strategy-scoped topics or event filtering?
3. **RunAnchor Management:** Different timestamps per strategy - how to manage?
4. **Resource Sharing:** Which singletons are truly shared vs per-strategy?

**Proposed Approach:**
```python
class ParallelRunService:
    def run_strategies(self, strategy_ids: list[str]):
        # Create isolated context per strategy
        for strategy_id in strategy_ids:
            context = StrategyExecutionContext(
                strategy_id=strategy_id,
                cache=self._get_or_create_cache(strategy_id),
                event_scope=f"strategy.{strategy_id}.*"
            )
            
            # Run in separate thread/async task
            self._executor.submit(self._run_strategy, context)
```

**Decision Needed:**
Design complete multi-strategy execution architecture (separate doc?)

**Impact:**
- All singleton components (StrategyCache, EventBus, TickCacheManager)
- ParallelRunService implementation
- Strategy isolation guarantees

---

## 🟢 MINOR GAPS (Edge Cases & Polish)

### GAP-009: STOP Disposition Cleanup Protocol Undefined

**Location:** `EVENT_DRIVEN_WIRING.md`

**Problem:**
STOP disposition triggers cleanup, but cleanup protocol is undefined:

```python
return DispositionEnvelope(disposition="STOP")
# EventAdapter publishes flow-stop event
# Then what?
```

**Questions:**
- Who is "FlowTerminator" (mentioned but not documented)?
- What cleanup happens? (Clear TickCache? Close connections? Persist state?)
- Can STOP be called mid-chain? (What happens to downstream workers?)
- Is cleanup synchronous or asynchronous?

**Decision Needed:**
Define explicit STOP cleanup protocol and FlowTerminator component.

**Impact:**
- EventAdapter implementation
- TickCacheManager lifecycle
- Platform shutdown sequence

---

### GAP-010: Worker Schema Double Validation Overhead

**Location:** `CONFIG_BUILDSPEC_TRANSLATION_DESIGN.md`

**Problem:**
Worker params validated twice without caching benefit:

```python
# ConfigTranslator validates
validated_params = schema_class.model_validate(entry.params)
spec.config_params = validated_params.model_dump()  # ← Convert to dict

# Worker validates again
self._params = schema_class.model_validate(spec.config_params)  # ← From dict
```

**Issue:**
Pydantic caching only works with identical objects. Dict → Model → Dict → Model loses cache.

**Performance Impact:**
50 workers = 100 validations (50% overhead)

**Design Question:**
Accept overhead as defense-in-depth, or optimize?

**Proposed Solutions:**
- Option A: BuildSpec stores Pydantic model (not dict)
- Option B: Worker trusts BuildSpec (no re-validation)
- Option C: Accept overhead (security > performance)

**Decision Needed:**
Choose validation strategy (security vs performance trade-off)

**Impact:**
- BuildSpec schema
- Worker constructor pattern
- Bootstrap performance

---

### GAP-011: RunAnchor Timezone Handling Undefined

**Location:** `POINT_IN_TIME_MODEL.md`

**Problem:**
RunAnchor timestamp has no timezone enforcement:

```python
class RunAnchor(BaseModel):
    timestamp: datetime  # Naive or aware? Which timezone?
```

**Scenario:**
```python
# TickCacheManager creates anchor
anchor = RunAnchor(timestamp=datetime.now(timezone.utc))  # UTC

# Worker requests data
df = self.ohlcv_provider.get_window(end_time=anchor.timestamp)

# Provider returns data in exchange timezone (EST)
# ❌ Timestamp mismatch - possible data leakage!
```

**Design Question:**
Should RunAnchor enforce timezone?

**Proposed Solutions:**
- Option A: Enforce UTC-aware (validation in RunAnchor)
- Option B: Provider converts to anchor timezone (responsibility on provider)
- Option C: Document convention (no enforcement)

**Decision Needed:**
Choose timezone handling strategy.

**Impact:**
- RunAnchor validation
- Provider interface contracts
- Data integrity guarantees

---

### GAP-012: BuildSpec Worker Class Circular Dependency

**Location:** `CONFIG_BUILDSPEC_TRANSLATION_DESIGN.md`

**Problem:**
BuildSpec needs worker class reference, but class is loaded by factory:

```python
class WorkerBuildSpec(BaseModel):
    worker_class: type  # ← How to get this?

# ConfigTranslator creates BuildSpec
spec = WorkerBuildSpec(
    worker_class=???  # Who loads the class?
)

# WorkerFactory loads class
worker = spec.worker_class(spec)
```

**Chicken-and-egg:**
ConfigTranslator needs class → Factory loads class → Factory needs BuildSpec

**Design Question:**
Who is responsible for loading worker classes?

**Proposed Solutions:**
- Option A: BuildSpec stores module path (string), Factory loads class
- Option B: PluginRegistry pre-loads all classes, ConfigTranslator references
- Option C: BuildSpec stores class reference, ConfigTranslator imports dynamically

**Decision Needed:**
Choose plugin loading strategy.

**Impact:**
- BuildSpec schema
- ConfigTranslator responsibilities
- PluginRegistry role

---

## 📋 Resolution Checklist

For each gap, mark when resolved:

### Critical (Must Fix Before Week 1)
- [ ] GAP-001: StrategyCache multi-tenancy → Decision: _________
- [ ] GAP-002: System event naming → Decision: _________
- [ ] GAP-003: PUBLISH payload location → Decision: _________
- [ ] GAP-004: EventAdapter ownership → Decision: _________

### Medium (Resolve During Implementation)
- [ ] GAP-005: ContextWorker enforcement → Decision: _________
- [ ] GAP-006: PlanningAggregator position → Decision: _________
- [ ] GAP-007: Causality ID duplication → Decision: _________
- [ ] GAP-008: Multi-strategy execution → Decision: _________

### Minor (Resolve Before Production)
- [ ] GAP-009: STOP cleanup protocol → Decision: _________
- [ ] GAP-010: Double validation overhead → Decision: _________
- [ ] GAP-011: RunAnchor timezone → Decision: _________
- [ ] GAP-012: BuildSpec class loading → Decision: _________

---

## 🎯 Next Steps

1. **Review Critical Gaps** (GAP-001 through GAP-004)
   - Discuss trade-offs for each proposed solution
   - Make explicit decisions
   - Update architecture docs with decisions

2. **Update Architecture Docs**
   - POINT_IN_TIME_MODEL.md (GAP-001, GAP-011)
   - EVENT_DRIVEN_WIRING.md (GAP-002, GAP-003, GAP-004)
   - PLATFORM_COMPONENTS.md (GAP-006)
   - CONFIG_BUILDSPEC_TRANSLATION_DESIGN.md (GAP-010, GAP-012)

3. **Create Decision Records**
   - Document WHY each decision was made
   - Include rejected alternatives with reasoning

4. **Archive This Document**
   - Move to `docs/development/#Archief/` when all gaps resolved
   - Reference from relevant architecture docs

---

**Document Status:** ACTIVE - Requires Decisions  
**Last Updated:** 2025-11-02  
**Review Required:** Before Week 1 Implementation

