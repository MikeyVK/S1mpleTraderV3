# Sessie Overdracht - 30 Oktober 2025

## Samenvatting

Architecturele discussie en documentatie update over **Event Wiring & Broadcast Pattern**. Belangrijkste inzicht: strikte scheiding tussen configuratie (routing topology) en filtering logic (handler code), met enforcement van SRP (Single Responsibility Principle) voor flow initiators.

---

## 1. Event Wiring Architecture - Broadcast Pattern

### Probleem Identificatie

Gebruiker identificeerde dat EVENT_LIFECYCLE_ARCHITECTURE.md incorrecte event flows toonde:
- OperationService leek meerdere specifieke events te publiceren (TICK_RECEIVED, NEWS_RECEIVED, etc.)
- In werkelijkheid: OperationService publiceert **ÉÉN generiek event** (`EXTERNAL_EVENT_RECEIVED`)
- Payload bevat discriminator: `ExternalEvent(event_type, event_data, priority, timestamp)`

### Architecturele Correctie

**VOOR (Incorrect):**
```python
# OperationService publiceert verschillende events
self.event_bus.publish(Event(name="TICK_RECEIVED", payload=tick_data))
self.event_bus.publish(Event(name="NEWS_RECEIVED", payload=news_data))
```

**NA (Correct - Broadcast Pattern):**
```python
# OperationService publiceert ÉÉN generiek event
self.event_bus.publish(Event(
    name="EXTERNAL_EVENT_RECEIVED",
    payload=ExternalEvent(
        event_type="TICK",  # Discriminator!
        event_data=tick_data,
        priority=priority,
        timestamp=timestamp
    )
))
```

**Filtering in Handlers:**
```python
class BaseFlowInitiator:
    def on_external_event(self, event: Event[ExternalEvent]) -> DispositionEnvelope:
        # Filter op payload.event_type (NIET event name!)
        if event.payload.event_type != self.get_event_type():
            return DispositionEnvelope(disposition=Disposition.CONTINUE)
        
        # Transform & publish als type matched
        flow_context = self.transform_payload(event.payload)
        return DispositionEnvelope(disposition=Disposition.PUBLISH, next_payload=flow_context)
```

---

## 2. Configuration Requirements - NO Filter Fields in Wiring Config

### Kernprincipe Vastgelegd

> **EventWiringDTO blijft simpel** (source + target only). Filtering gebeurt **consistent op DTO inhoud basis** in worker handlers, NIET in configuratie. **Geen payload_filter velden, geen hints in YAML.**

### WiringRuleDTO Schema (Definitief)

```python
class WiringSourceDTO(BaseModel):
    component_id: str
    event_name: str
    event_type: str
    # ✅ NO payload_filter field!
    # ✅ NO filter_condition hints!
    # ✅ NO when clauses!

class WiringTargetDTO(BaseModel):
    component_id: str
    handler_method: str

class WiringRuleDTO(BaseModel):
    wiring_id: str
    source: WiringSourceDTO
    target: WiringTargetDTO
    # ✅ ONLY routing topology - NO filtering logic!
```

### YAML Configuration Pattern

**✅ CORRECT - Broadcast Pattern (4 rules, same event):**
```yaml
platform_wiring:
  - wiring_id: "os_to_tick_manager"
    source:
      component_id: "operation_service"
      event_name: "EXTERNAL_EVENT_RECEIVED"  # Generic!
      event_type: "ExternalEvent"
    target:
      component_id: "tick_cache_manager"
      handler_method: "on_external_event"
  
  # ... 3 more rules (news, scheduled_task, user_action)
  # All listen to SAME event: EXTERNAL_EVENT_RECEIVED
```

**❌ DEPRECATED - Specific Events:**
```yaml
# FOUT - Dit suggereert 4 verschillende events
platform_wiring:
  - source:
      event_name: "TICK_RECEIVED"  # Deprecated!
```

**❌ WRONG - Filter Fields in Config:**
```yaml
# FOUT - Filtering hoort in handler code!
platform_wiring:
  - source:
      event_name: "EXTERNAL_EVENT_RECEIVED"
      payload_filter:  # ❌ NO! Architecture violation!
        event_type: "TICK"
```

### Rationale

**Waarom GEEN filter velden in config?**
- **Separation of Concerns:** Wiring = routing topology, Filtering = business logic (in handlers)
- **Type Safety:** Handlers receive full DTO, can inspect all fields in type-safe code
- **Flexibility:** Change filtering logic without config changes
- **Testability:** Filter logic in code = unit testable Python, not YAML strings

---

## 3. SRP Enforcement - Flow Initiators

### Probleem: Feature Creep in Flow Initiator Config

Agent had initieel flow initiator configuratie toegevoegd met:
- ❌ Rolling window config (hoort bij MTF Provider!)
- ❌ Cache settings (hoort bij MTF Provider!)
- ❌ News filtering op impact level (hoort bij Strategy workers!)
- ❌ Deduplication logic (aparte platform service)
- ❌ Rate limiting (OperationService queue)
- ❌ Task execution config (aparte task executor)

### Correctie: Strikte SRP

**Flow Initiator = DUMB Router (ÉÉN verantwoordelijkheid):**
- ✅ Filter op `event.payload.event_type`
- ✅ Check `should_start_flow()` (optioneel, bijv. MTF Provider ready check)
- ✅ Transform `ExternalEvent.event_data` → flow context DTO
- ✅ Publish flow start event

**NIET verantwoordelijk:**
- ❌ Rolling window management → MTF Provider
- ❌ Cache configuratie → MTF Provider
- ❌ Business logic filtering → Strategy workers
- ❌ Deduplication → Aparte platform service
- ❌ Rate limiting → OperationService queue
- ❌ Task execution → Aparte task executor
- ❌ Authorization → Aparte auth service

### Conclusie: Flow Initiators Hebben GEEN Config

Flow initiators zijn **pure transformers** - filtering logic is hardcoded (`get_event_type()`), transformatie is DTO mapping. Geen configuratie nodig, dus:
- ✅ Geen schema's voor flow initiator config
- ✅ Geen YAML voorbeelden in CONFIG_SCHEMA_ARCHITECTURE
- ✅ Implementatie details horen in DESIGN docs, niet CONFIG docs

---

## 4. Documentatie Updates

### Aangepaste Documenten

#### 4.1 EVENT_LIFECYCLE_ARCHITECTURE.md

**Toegevoegd:**
- Sectie 10: Configuration Requirements - Broadcast Pattern Implications
- WiringRuleDTO schema constraints (NO filter fields)
- Broadcast pattern YAML voorbeelden (correct vs deprecated)
- Handler-based filtering contract (`BaseFlowInitiator.get_event_type()`)
- BroadcastPatternValidator implementation voor bootstrap validation
- Configuration impact summary table (6 aspecten)

**Gecorrigeerd:**
- Alle event flow diagrams: ONE generic event (`EXTERNAL_EVENT_RECEIVED`)
- ExternalEvent DTO documentatie met discriminator pattern
- BaseFlowInitiator.on_external_event() met payload filtering
- Platform wiring rules: 4 rules voor flow initiators (all same event)

#### 4.2 CONFIG_SCHEMA_ARCHITECTURE.md

**Toegevoegd:**
- Broadcast Pattern Configuration Requirements (vóór Implementation Strategy)
- WiringRule schema constraints met rationale
- BroadcastPatternValidator validation logic
- YAML configuration examples (correct vs deprecated vs wrong)
- Handler-based filtering contract
- Configuration impact summary table

**Verwijderd:**
- ❌ Flow Initiator Configuration sectie (400+ regels)
- ❌ Implementatie voorbeelden (vol aannames/fouten)
- ❌ Config schemas voor componenten zonder config needs
- ❌ Code die niet in CONFIG document hoort

**Rationale verwijdering:**
- Document moet focussen op **configuratie schemas**
- Flow initiators hebben geen config nodig
- Implementatie details horen in DESIGN docs
- Voorkomen van feature creep in documentatie

#### 4.3 PLATFORM_VS_STRATEGY_WIRING.md

**Toegevoegd:**
- Broadcast Pattern Configuration Requirements in Conclusie sectie
- WiringRuleDTO simplicity principe
- Platform wiring broadcast pattern (4 rules voor flow initiators)
- Handler-based filtering implementation
- BroadcastPatternValidator validation logic
- Updated "De Grens" diagram met broadcast pattern

**Key Principles:**
- Platform wiring = Infrastructure lijm (singletons) + Broadcast pattern
- Strategy wiring = Business logic flow (workers)
- **Filtering = Handler code** (NIET in wiring config!)

---

## 5. Architecturele Principes (Herbevestigd)

### 5.1 Plugin-First Principe

**Platform componenten = DUMB:**
- ✅ Platform doet ALLEEN technische routing
- ✅ GEEN quant parameters in platform config
- ✅ GEEN business logic filtering in platform layer

**Strategy workers = SMART:**
- ✅ ALL business logic in strategy plugins
- ✅ ALL quant parameters in strategy config (min_severity, sources, thresholds)
- ✅ Workers filteren op DTO inhoud (niet platform config)

### 5.2 Broadcast + Filter Pattern

**EventBus:**
- ✅ Broadcast naar ALLE listeners (dumb routing)
- ✅ Workers filteren zelf op payload discriminator
- ✅ Event name is generic, payload heeft discriminator

**Config:**
- ✅ Multiple rules, same event name = broadcast pattern
- ✅ NO filter velden in wiring config
- ✅ Filtering logic = handler code (type-safe, testable)

### 5.3 SRP (Single Responsibility Principle)

**Flow Initiators:**
- ✅ ÉÉN verantwoordelijkheid: event type routing
- ✅ < 50 LOC per initiator (pure transformers)
- ✅ GEEN config (hardcoded filtering logic)
- ✅ Delegate complexe taken (rolling windows → MTF Provider)

**Separation of Concerns:**
- Platform layer: HOW flows are initiated (routing topology)
- Strategy layer: WHAT happens in flows (business logic)
- Provider layer: Data/state management (MTF, cache, persistence)

---

## 6. Bootstrap Validation Requirements

### BroadcastPatternValidator

**Must validate at bootstrap:**

```python
class BroadcastPatternValidator:
    def validate_flow_initiator_wiring(self, wiring_rules):
        """Ensure broadcast pattern consistency."""
        flow_initiators = [
            "tick_cache_manager",
            "news_event_manager",
            "scheduled_task_manager", 
            "user_action_manager"
        ]
        
        for initiator in flow_initiators:
            # 1. Check: Exactly ONE wiring rule per initiator
            # 2. Check: Event name = "EXTERNAL_EVENT_RECEIVED"
            # 3. Check: Handler method = "on_external_event"
    
    def validate_no_deprecated_events(self, wiring_rules):
        """Reject deprecated specific events."""
        deprecated = [
            "TICK_RECEIVED",
            "NEWS_RECEIVED", 
            "SCHEDULED_TASK_TRIGGERED",
            "USER_ACTION_RECEIVED"
        ]
        # Fail if any deprecated event found
```

---

## 7. Breaking Changes & Migration

### 7.1 Event Names

| **OLD (Deprecated)** | **NEW (Broadcast)** |
|---------------------|---------------------|
| `TICK_RECEIVED` | `EXTERNAL_EVENT_RECEIVED` (event_type="TICK") |
| `NEWS_RECEIVED` | `EXTERNAL_EVENT_RECEIVED` (event_type="NEWS") |
| `SCHEDULED_TASK_TRIGGERED` | `EXTERNAL_EVENT_RECEIVED` (event_type="SCHEDULED_TASK") |
| `USER_ACTION_RECEIVED` | `EXTERNAL_EVENT_RECEIVED` (event_type="USER_ACTION") |

### 7.2 Wiring Config

**Before:**
- 4 wiring rules met verschillende event names
- Event name was discriminator

**After:**
- 4 wiring rules met ZELFDE event name (`EXTERNAL_EVENT_RECEIVED`)
- Payload discriminator: `event.payload.event_type`

### 7.3 Handler Implementation

**All flow initiators must:**
- Implement `get_event_type()` abstract method
- Filter in `on_external_event()` via payload inspection
- Return early if event type doesn't match

---

## 8. Actiepunten voor Volgende Sessie

### HIGH Priority

1. **OperationService Update**
   - [ ] Implement generic event publishing (`EXTERNAL_EVENT_RECEIVED`)
   - [ ] Create `ExternalEvent` DTO with discriminator
   - [ ] Update event queue to use generic events

2. **BaseFlowInitiator Implementation**
   - [ ] Create abstract base class with template method
   - [ ] Implement `get_event_type()` abstract method
   - [ ] Add payload filtering in `on_external_event()`
   - [ ] Ensure < 50 LOC per concrete implementation

3. **Bootstrap Validation**
   - [ ] Implement `BroadcastPatternValidator`
   - [ ] Add validation checks to EventWiringFactory
   - [ ] Fail fast on deprecated events or missing wirings

### MEDIUM Priority

4. **Platform Wiring Config**
   - [ ] Update `platform_wiring.yaml` template
   - [ ] Update all 4 flow initiator wirings to broadcast pattern
   - [ ] Document in config examples

5. **Testing**
   - [ ] Unit tests voor BaseFlowInitiator template method
   - [ ] Unit tests voor payload filtering logic
   - [ ] Integration tests voor broadcast pattern
   - [ ] Bootstrap validation tests (positive + negative cases)

### LOW Priority

6. **Documentation Cleanup**
   - [ ] Review andere docs voor deprecated event names
   - [ ] Update sequence diagrams met broadcast pattern
   - [ ] Add migration guide voor oude configs

---

## 9. Lessen Geleerd

### 9.1 Documentatie Scope

**Fout:** Implementatie code in CONFIG_SCHEMA_ARCHITECTURE document
**Correctie:** Config docs voor schemas, DESIGN docs voor implementaties
**Principe:** Elk document heeft ÉÉN verantwoordelijkheid (SRP geldt ook voor docs!)

### 9.2 Feature Creep Detectie

**Fout:** Flow initiator config vol met niet-gerelateerde features (cache, filtering, rate limiting)
**Correctie:** Strikte SRP - flow initiators doen ALLEEN event type routing
**Principe:** Als component geen config nodig heeft, voeg dan geen config schema toe!

### 9.3 Separation of Concerns

**Fout:** Platform config met business logic parameters
**Correctie:** Platform = technical routing, Strategy = business logic
**Principe:** Plugin-First - platform is framework, quants pluggen logic in

### 9.4 Onderhoud Nachtmerrie Preventie

**Fout:** Zelfde informatie in 3 verschillende documenten
**Correctie:** Ééń centrale plek voor elk onderwerp
**Principe:** DRY (Don't Repeat Yourself) geldt ook voor documentatie!

---

## 10. Architecturele Zuiverheid Checklist

**✅ Plugin-First:**
- Platform componenten ZONDER quant parameters
- Strategy workers MET business logic filtering
- Clear separation: framework vs plugins

**✅ SRP Overal:**
- Flow initiators: < 50 LOC, ÉÉN verantwoordelijkheid
- WiringRuleDTO: ALLEEN routing topology
- Filtering logic: Handler code, NIET config

**✅ Broadcast + Filter:**
- EventBus: Dumb routing (broadcast to all)
- Workers: Smart filtering (payload inspection)
- Config: NO filter velden

**✅ Type Safety:**
- Handlers receive full DTO
- Filtering in type-safe Python code
- Compiler prevents mistakes

**✅ Testability:**
- Filter logic = unit testable
- NO YAML parsing in tests
- Pure functions, easy to test

---

**Sessie Datum:** 30 Oktober 2025  
**Volgende Sessie:** TBD  
**Status:** Architectuur gedocumenteerd, klaar voor implementatie
