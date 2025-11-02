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

### GAP-002: System Event Naming - UUID vs Static Wiring ✅ RESOLVED (NON-ISSUE)

**Location:** `EVENT_DRIVEN_WIRING.md`

**Initial Problem:**
Documentation initially suggested system events use **runtime-generated UUIDs**, creating an impossible situation where static `strategy_wiring_map.yaml` would need to contain event names that don't exist yet.

**Root Cause Analysis:**
This was a **misunderstanding** of the V3 architecture. After reviewing the Strategy Builder UI documentation and addenda, the actual design is:

**DECISION: UI-Generated Event Names at Configuration Time (Existing V3 Design)**

**How It Actually Works:**

### **Phase 1: Strategy Building (UI Session)**

The **Strategy Builder UI** generates unique event names **during the configuration phase** (NOT runtime):

```typescript
// Strategy Builder UI (TypeScript)
function onWorkerPlaced(worker: WorkerInstance, slot: Slot, position: number) {
    // Generate unique event name DURING UI SESSION
    const eventName = `_${worker.instance_id}_OUTPUT_${generateUID()}`;
    
    // Store in strategy_wiring_map.yaml
    addWiringRule({
        source: {
            component_id: worker.instance_id,
            event_name: eventName,  // ✅ Generated NOW, not at runtime
            event_type: "SystemEvent"
        },
        target: {
            component_id: nextWorker.instance_id,
            handler_method: "process"
        }
    });
}
```

**Generated `strategy_wiring_map.yaml`:**
```yaml
# Generated by Strategy Builder UI on 2025-11-02 14:30:00
wiring_rules:
  - wiring_id: "ema_fast_to_ema_slow"
    source:
      component_id: "ema_detector_instance_1"
      event_name: "_ema_detector_instance_1_OUTPUT_abc123"  # ✅ UI-generated
      event_type: "SystemEvent"
    target:
      component_id: "ema_detector_instance_2"
      handler_method: "process"
```

### **Phase 2: Bootstrap (ConfigTranslator)**

ConfigTranslator reads the **UI-generated** `strategy_wiring_map.yaml` and copies event names into BuildSpecs:

```python
# backend/config/config_translator.py
class ConfigTranslator:
    def translate_strategy_wiring(
        self, 
        strategy_wiring_map: dict
    ) -> WiringBuildSpec:
        # Read UI-generated wiring rules
        wiring_rules = []
        for rule in strategy_wiring_map["wiring_rules"]:
            wiring_rules.append(
                WiringRule(
                    source=WiringSource(
                        component_id=rule["source"]["component_id"],
                        event_name=rule["source"]["event_name"],  # From UI
                        event_type=rule["source"]["event_type"]
                    ),
                    target=WiringTarget(
                        component_id=rule["target"]["component_id"],
                        handler_method=rule["target"]["handler_method"]
                    )
                )
            )
        
        return WiringBuildSpec(wiring_rules=wiring_rules)
```

### **Phase 3: Assembly (EventWiringFactory)**

EventWiringFactory configures EventAdapters with the **UI-generated** event names from BuildSpecs:

```python
# backend/assembly/event_wiring_factory.py
class EventWiringFactory:
    def create_adapters(
        self,
        strategy_id: str,
        workers: Dict[str, IWorker],
        wiring_spec: WiringBuildSpec
    ) -> Dict[str, EventAdapter]:
        # Build system event publications from wiring_spec
        system_publications = {}
        for rule in wiring_spec.wiring_rules:
            if rule.source.event_type == "SystemEvent":
                component_id = rule.source.component_id
                if component_id not in system_publications:
                    system_publications[component_id] = {}
                
                # Map CONTINUE disposition to UI-generated event name
                system_publications[component_id]["CONTINUE"] = rule.source.event_name
        
        # Create adapters with configured event names
        adapters = {}
        for component_id, worker in workers.items():
            adapter = EventAdapter(
                component_id=component_id,
                worker=worker,
                event_bus=self._event_bus,
                strategy_id=strategy_id,
                system_event_publications=system_publications.get(component_id, {})
            )
            adapters[component_id] = adapter
        
        return adapters
```

### **Phase 4: Runtime (EventAdapter Execution)**

EventAdapter publishes using the **pre-configured** event name (from UI):

```python
# backend/core/event_adapter.py (Runtime)
class EventAdapter:
    def handle_worker_result(self, envelope: DispositionEnvelope):
        if envelope.disposition == Disposition.CONTINUE:
            # Use PRE-CONFIGURED event name (from UI via BuildSpecs)
            event_name = self._system_event_publications["CONTINUE"]
            # Example: "_ema_detector_instance_1_OUTPUT_abc123"
            
            self._event_bus.publish(
                event_name=event_name,
                payload=envelope.payload,
                scope=ScopeLevel.STRATEGY,
                strategy_instance_id=self._strategy_id
            )
```

**Timeline:**
```
1. UI Session (2025-11-02 14:30)
   └─ User drags workers
   └─ UI generates event names: "_ema_fast_OUTPUT_abc123"
   └─ Saves to strategy_wiring_map.yaml

2. Bootstrap (strategy startup)
   └─ ConfigTranslator reads strategy_wiring_map.yaml
   └─ Copies event names to BuildSpecs
   └─ EventWiringFactory configures adapters with these names

3. Runtime (per tick)
   └─ EventAdapter publishes using pre-configured names
   └─ NO UUID generation at runtime
```

**Why This Works:**
- ✅ **Static Configuration:** All event names exist in `strategy_wiring_map.yaml` before runtime
- ✅ **UI Responsibility:** Strategy Builder generates unique names during configuration
- ✅ **No Runtime Generation:** EventAdapter uses pre-configured names from BuildSpecs
- ✅ **Predictable Wiring:** Subscribers know exact event names at bootstrap time

**Architectural Principle:**
> "The Strategy Builder UI is the **event name authority**. It generates all system event names during strategy construction, ensuring the `strategy_wiring_map.yaml` is a complete, static specification that requires NO runtime name generation."

**Decision:** ✅ **CONFIRMED - UI-Generated Event Names (V3 Existing Design)**

**Impact:**
- ✅ No changes needed - V3 architecture already correct
- ✅ EventBus remains simple (no pattern matching needed)
- ✅ Wiring map is static and complete
- ⚠️ EVENT_DRIVEN_WIRING.md - clarify UI generates event names at configuration time
- ⚠️ Strategy Builder UI documentation - emphasize event name generation responsibility

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

