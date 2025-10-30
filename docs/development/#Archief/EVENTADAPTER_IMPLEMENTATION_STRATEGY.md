# EventAdapter Implementation Strategy

**Date:** 2025-10-30  
**Context:** Design complete, ready for phased implementation  
**Status:** Strategy Approved

---

## TL;DR - De Strategie

**Week 2 (NU):** EventAdapter implementeren met **mocked BuildSpec data**  
**Week 3:** Config schemas + Bootstrap components (BLOCKER voor factories)  
**Week 5:** EventWiringFactory implementeren (met ECHTE BuildSpecs)

---

## Kernbeslissingen uit Analyse

### 1. ✅ Handler Validation → ConfigValidator (NIET EventAdapter)

**Waar:**
```
ConfigValidator (Bootstrap - Phase 5)
    ↓
- Validate worker params (via worker schema.py)
- Validate handler methods exist (via manifest.invokes)  ← HIER!
- Validate event names match (publishes vs wiring)
- Circular dependency detection
    ↓
ConfigTranslator (NO validation - pure translation)
    ↓
BuildSpecs (pre-validated)
    ↓
EventAdapter (pure execution, assumes valid BuildSpecs)
```

**Rationale:**
- ✅ Fail-fast tijdens bootstrap (niet runtime)
- ✅ Separation of concerns (validation vs execution)
- ✅ EventAdapter blijft simpel (pure glue logic)

**Reference:** `docs/development/CONFIG_BUILDSPEC_TRANSLATION_DESIGN.md` Step 2

### 2. ✅ NO Event Name Generation - Pre-Configured

**Complete Lifecycle:**
```
UI Strategy Builder
    ↓ Generates ALL event names (UUID/timestamp based)
strategy_wiring_map.yaml
    ↓ Contains concrete event names
ConfigTranslator
    ↓ Passes through (NO generation)
BuildSpecs.wiring_specs
    ↓ Same pre-configured event names
EventWiringFactory
    ↓ Reads from BuildSpecs
EventAdapter
    ↓ Executes with pre-configured names
```

**EventAdapter heeft GEEN generatie methods:**
- ❌ ~~`_generate_system_event_name()`~~ REMOVED
- ❌ ~~`_generate_stop_event_name()`~~ REMOVED
- ✅ Uses `system_event_publications` dict (pre-configured)

**Reference:** `docs/development/EVENTADAPTER_DESIGN.md` - Wiring Map Lifecycle

### 3. 🐔🥚 Dependency Order - Config Schemas FIRST

**Probleem:**
```
EventWiringFactory needs:
    - BuildSpecs ❌ (niet gedefinieerd)
    - PluginRegistry ❌ (niet geïmplementeerd)
    - WorkerFactory ❌ (niet geïmplementeerd)

EventAdapter needs:
    - Pre-configured wiring (from BuildSpecs) ❌
```

**Oplossing - Nieuwe Volgorde:**
```
Week 2: EventAdapter (mock-based implementation)
    ↓
Week 3: Config Schemas + Bootstrap Design (BLOCKER!)
    ↓ Pydantic DTOs: Manifest, Wiring, Blueprint, BuildSpecs
    ↓ ConfigLoader, ConfigValidator, ConfigTranslator designs
    ↓
Week 4: Bootstrap Implementation
    ↓ YAML → BuildSpecs pipeline werkend
    ↓
Week 5: Factories (NU PAS MOGELIJK)
    ↓ PluginRegistry, WorkerFactory, EventWiringFactory
    ↓
Week 6: Integration (EventAdapter + ECHTE BuildSpecs)
```

### 4. 🎯 Wat kunnen we NU - Mock-Based Implementation

**Beschikbare Components:**
- ✅ IEventBus + EventBus (33 tests passing)
- ✅ IWorker + IWorkerLifecycle (13 tests passing)
- ✅ IStrategyCache + StrategyCache (20 tests passing)
- ✅ DispositionEnvelope DTO (17 tests passing)

**EventAdapter Mock-Based Tests:**
```python
def test_event_adapter_continue_disposition():
    """EventAdapter publishes pre-configured system event on CONTINUE."""
    mock_bus = Mock(spec=IEventBus)
    mock_worker = Mock(spec=IWorker)
    mock_worker.process.return_value = DispositionEnvelope(
        disposition=Disposition.CONTINUE
    )
    
    # Mock BuildSpec data (handmatig voor tests)
    adapter = EventAdapter(
        component_id="test_worker",
        worker=mock_worker,
        event_bus=mock_bus,
        strategy_id="test_strategy",
        subscriptions=["_TICK_START"],
        handler_mapping={"_TICK_START": "process"},
        allowed_publications=set(),
        system_event_publications={
            "CONTINUE": "_test_worker_OUTPUT_abc123"  # Mock value
        }
    )
    
    # Simulate event from EventBus
    adapter._on_event_received("_TICK_START", None)
    
    # Verify correct system event published
    mock_bus.publish.assert_called_once_with(
        event_name="_test_worker_OUTPUT_abc123",
        payload=None,
        scope="STRATEGY",
        strategy_id="test_strategy"
    )
```

**Voordelen Mock-Based Aanpak:**
- ✅ EventAdapter volledig implementeren (business logic compleet)
- ✅ Constructor signature definiëren (wat EventWiringFactory moet leveren)
- ✅ Alle edge cases testen (dispositions, validation, errors)
- ✅ Foundation voor later (als BuildSpecs klaar zijn)

**Nadelen:**
- ⚠️ Geen ECHTE BuildSpecs (nog niet gedefinieerd)
- ⚠️ EventWiringFactory kan nog niet (blocker: BuildSpecs)
- ⚠️ Geen end-to-end integration tests (komt Week 6)

---

## Implementatie Roadmap

### Week 2: Platform Components (NU) 🔄

**EventAdapter - Mock-Based Implementation:**

1. **Class Implementation**
   ```python
   # backend/assembly/event_adapter.py
   class EventAdapter:
       def __init__(
           self,
           component_id: str,
           worker: IWorker,
           event_bus: IEventBus,
           strategy_id: str,
           subscriptions: list[str],              # Pre-configured
           handler_mapping: Dict[str, str],       # Pre-configured
           allowed_publications: Set[str],        # Pre-configured
           system_event_publications: Dict[str, str]  # Pre-configured
       ): ...
   ```

2. **Core Methods**
   - `_subscribe_to_events()` - Subscribe on init
   - `_on_event_received()` - EventBus callback
   - `_handle_disposition()` - Dispatcher
   - `_handle_continue_disposition()` - System event publish
   - `_handle_publish_disposition()` - Custom event + validation
   - `_handle_stop_disposition()` - Flow termination
   - `_validate_custom_event()` - Manifest check
   - `shutdown()` - Cleanup

3. **Unit Tests (TDD)** - 15+ tests
   - Subscription on init
   - Worker invocation on event
   - CONTINUE disposition (system event published)
   - PUBLISH disposition (valid custom event)
   - PUBLISH disposition (invalid event - raises)
   - STOP disposition (stop event published)
   - Shutdown cleanup (unsubscribe all)
   - Multiple subscriptions
   - Multiple handlers
   - Error handling

**Other Week 2 Components:**

4. **TickCacheManager**
   - Design + Implementation
   - Run lifecycle orchestration
   - No BuildSpec dependencies

5. **Aggregators (Design)**
   - ContextAggregator design
   - PlanningAggregator design

**Milestone:** EventAdapter + TickCacheManager implemented (mock-tested)

---

### Week 3: Config Schemas + Bootstrap Design ⚠️ CRITICAL PATH

**BLOCKER voor EventWiringFactory en alle Factories!**

**Pydantic Schema DTOs:**

1. **WorkerManifestDTO**
   ```python
   class WorkerManifestDTO(BaseModel):
       plugin_id: str
       plugin_type: str  # "context", "signal", "threat", "planning"
       produces_dtos: list[str]  # Output DTO class names
       requires_dtos: list[str]  # Input DTO class names
       publishes: list[str]      # Custom events worker may publish
       invokes: dict[str, str]   # event_name → handler_method
       schema: SchemaReference   # Path to worker's schema.py
       capabilities: list[str]
   ```

2. **WiringRuleDTO**
   ```python
   class WiringSourceDTO(BaseModel):
       component_id: str
       event_name: str          # Pre-generated by UI
       event_type: Literal["SystemEvent", "CustomEvent"]
   
   class WiringTargetDTO(BaseModel):
       component_id: str
       handler_method: str      # Must exist on worker
   
   class WiringRuleDTO(BaseModel):
       wiring_id: str
       source: WiringSourceDTO
       target: WiringTargetDTO
   ```

3. **StrategyBlueprintDTO**
   ```python
   class StrategyBlueprintDTO(BaseModel):
       strategy_id: str
       workers: list[WorkerInstanceDTO]
       wiring: WiringConfigDTO
   ```

4. **BuildSpec DTOs**
   ```python
   class WorkerBuildSpec(BaseModel):
       worker_class: type
       config_params: dict[str, Any]  # Pre-validated by ConfigValidator
       manifest: WorkerManifestDTO
       capabilities: list[str]
   
   class WiringBuildSpec(BaseModel):
       wiring_rules: list[WiringRuleDTO]  # Same as config
   
   class StrategyBuildSpec(BaseModel):
       strategy_id: str
       workers: list[WorkerBuildSpec]
       wiring: WiringBuildSpec
   ```

**Bootstrap Components Design:**

5. **ConfigLoader**
   - YAML → Generic Pydantic models
   - Structure validation ONLY
   - No worker-specific validation

6. **ConfigValidator** ⭐ CRITICAL
   - **Worker params validation** (via worker schema.py)
   - **Handler method validation** ← KEY!
     ```python
     def _validate_handler_exists(
         self, 
         worker_class: type, 
         handler_method: str
     ) -> None:
         if not hasattr(worker_class, handler_method):
             raise ConfigValidationError(
                 f"Worker {worker_class} missing handler: {handler_method}"
             )
     ```
   - **Event name consistency** (publishes vs wiring)
   - **Component reference validation**
   - **Circular dependency detection**

7. **ConfigTranslator**
   - Validated config → BuildSpecs
   - NO validation (trusts ConfigValidator)
   - Pure translation logic

**Milestone:** Config pipeline designed, BuildSpec format frozen

---

### Week 4: Bootstrap Implementation

1. ConfigLoader implementation + tests
2. ConfigValidator implementation + tests (handler validation!)
3. ConfigTranslator implementation + tests

**Milestone:** YAML → BuildSpecs pipeline werkend

---

### Week 5: Factories (NU PAS MOGELIJK)

**EventWiringFactory - ECHTE BuildSpecs:**

1. **Implementation**
   ```python
   class EventWiringFactory:
       def create_adapters(
           self,
           strategy_id: str,
           workers: Dict[str, IWorker],
           wiring_spec: WiringBuildSpec  # From ConfigTranslator
       ) -> Dict[str, EventAdapter]:
           """Create EventAdapters from BuildSpecs."""
           # Build maps from wiring_spec
           subscription_map = self._build_subscription_map(wiring_spec)
           handler_map = self._build_handler_mapping(wiring_spec)
           publications_map = self._build_publications_map(wiring_spec)
           system_publications_map = self._build_system_publications_map(
               wiring_spec
           )
           
           # Create adapters
           adapters = {}
           for component_id, worker in workers.items():
               adapter = EventAdapter(
                   component_id=component_id,
                   worker=worker,
                   event_bus=self._event_bus,
                   strategy_id=strategy_id,
                   subscriptions=subscription_map.get(component_id, []),
                   handler_mapping=handler_map.get(component_id, {}),
                   allowed_publications=publications_map.get(component_id, set()),
                   system_event_publications=system_publications_map.get(
                       component_id, {}
                   )
               )
               adapters[component_id] = adapter
           
           return adapters
   ```

2. **Helper Methods**
   - `_build_subscription_map()` - Extract target components
   - `_build_handler_mapping()` - Map events → methods
   - `_build_publications_map()` - Extract custom events
   - `_build_system_publications_map()` - Extract system events

3. **Tests**
   - Adapter creation from BuildSpecs
   - Subscription map building
   - Handler mapping building
   - Publications map building

**Other Factories:**

4. PluginRegistry (plugin discovery)
5. WorkerFactory (worker instantiation from BuildSpecs)
6. StrategyFactory (orchestration)

**Milestone:** Complete strategy assembly working

---

### Week 6: Integration

**End-to-End Tests:**

1. **Full Worker Chain**
   ```python
   def test_ema_to_regime_to_momentum_chain():
       """Test complete worker chain via EventAdapters + REAL BuildSpecs."""
       # 1. Load strategy config (YAML)
       strategy_config = load_yaml("strategies/btc_momentum.yaml")
       
       # 2. Bootstrap pipeline
       config_loader = ConfigLoader()
       config_validator = ConfigValidator()
       config_translator = ConfigTranslator()
       
       loaded_config = config_loader.load(strategy_config)
       config_validator.validate(loaded_config)
       build_specs = config_translator.translate(loaded_config)
       
       # 3. Build strategy
       plugin_registry = PluginRegistry()
       worker_factory = WorkerFactory(plugin_registry)
       wiring_factory = EventWiringFactory(event_bus)
       strategy_factory = StrategyFactory(
           worker_factory, 
           wiring_factory
       )
       
       strategy = strategy_factory.build(build_specs)
       
       # 4. Execute tick
       event_bus.publish("_TICK_FLOW_START", None, "STRATEGY", "btc_momentum")
       
       # 5. Verify chain executed
       assert strategy_cache.has_result("ema_detector_instance_1")
       assert strategy_cache.has_result("regime_classifier_instance_1")
       assert strategy_cache.has_result("momentum_scout_instance_1")
       
       # 6. Verify custom event published
       published_events = get_published_events(event_bus)
       assert "MOMENTUM_OPPORTUNITY" in published_events
   ```

2. **Custom Event Flow**
3. **Multi-Subscriber Events**
4. **Error Scenarios**

**Milestone:** Complete event-driven pipeline operational

---

## Test Strategy

### Unit Tests (Week 2 - Mock-Based)

**EventAdapter Tests (15+ tests):**

```python
# tests/unit/assembly/test_event_adapter.py

def test_adapter_subscribes_on_init():
    """EventAdapter subscribes to all events on initialization."""
    ...

def test_adapter_invokes_worker_on_event():
    """EventAdapter invokes correct worker method when event received."""
    ...

def test_adapter_continue_publishes_system_event():
    """CONTINUE disposition publishes pre-configured system event."""
    ...

def test_adapter_publish_validates_custom_event():
    """PUBLISH disposition validates event against allowed_publications."""
    ...

def test_adapter_publish_rejects_undeclared_event():
    """PUBLISH disposition raises ValueError for undeclared event."""
    ...

def test_adapter_stop_publishes_stop_event():
    """STOP disposition publishes pre-configured stop event."""
    ...

def test_adapter_shutdown_unsubscribes():
    """Shutdown unsubscribes all events."""
    ...

def test_adapter_multiple_subscriptions():
    """Adapter handles multiple event subscriptions."""
    ...

def test_adapter_missing_handler_mapping():
    """Adapter raises if event has no handler mapping."""
    ...

def test_adapter_worker_returns_wrong_type():
    """Adapter raises if worker returns non-DispositionEnvelope."""
    ...
```

### Integration Tests (Week 6 - Real BuildSpecs)

**EventWiringFactory Tests:**

```python
# tests/integration/test_event_wiring_factory.py

def test_factory_creates_adapters_from_buildspecs():
    """Factory creates EventAdapters from real BuildSpecs."""
    ...

def test_factory_builds_subscription_map():
    """Factory correctly maps events to target workers."""
    ...

def test_factory_builds_handler_mapping():
    """Factory correctly maps events to handler methods."""
    ...
```

**Full Pipeline Tests:**

```python
# tests/integration/test_event_driven_pipeline.py

def test_worker_chain_execution():
    """Test complete worker chain via EventBus."""
    ...

def test_custom_event_publication():
    """Test custom event publication and multi-subscriber."""
    ...
```

---

## Success Criteria

### Week 2 Complete
- ✅ EventAdapter class implemented
- ✅ 15+ unit tests passing (mock-based)
- ✅ TickCacheManager implemented
- ✅ Constructor signature frozen (defines EventWiringFactory contract)

### Week 3 Complete
- ✅ All config schema DTOs defined
- ✅ ConfigValidator design includes handler validation
- ✅ BuildSpec format frozen
- ✅ Bootstrap pipeline designed

### Week 5 Complete
- ✅ EventWiringFactory implemented
- ✅ EventAdapter + ECHTE BuildSpecs werkend
- ✅ All factories operational

### Week 6 Complete
- ✅ End-to-end integration tests passing
- ✅ Complete event-driven pipeline operational
- ✅ Custom events + multi-subscriber working

---

## Design Document Updates

### Updated Sections

1. **Open Questions** - Resolved
   - Question 1: UI generates event names (persisted in YAML)
   - Question 2: ConfigValidator validates handlers (NOT EventAdapter)
   - Question 3: Multi-handler support (KEEP flexible)

2. **Implementation Checklist** - Removed
   - ❌ `_generate_system_event_name()` (contradicts pre-configured principle)
   - ❌ `_generate_stop_event_name()` (contradicts pre-configured principle)
   - ✅ Added note: EventWiringFactory blocked by BuildSpecs

3. **Dependencies** - Clarified
   - EventAdapter: Can implement NOW (mock-based)
   - EventWiringFactory: Blocked until Week 5 (needs BuildSpecs)

---

## Related Documentation

- **EventAdapter Design:** `docs/development/EVENTADAPTER_DESIGN.md`
- **Config Pipeline Design:** `docs/development/CONFIG_BUILDSPEC_TRANSLATION_DESIGN.md`
- **TODO Updates:** `docs/TODO.md` (Week 2-6 roadmap)
- **Clarifications:** `docs/TODO_CLARIFICATIONS_20251030.md`

---

**Document Owner:** Development Team  
**Last Updated:** 2025-10-30  
**Status:** Strategy Approved - Ready for Implementation
