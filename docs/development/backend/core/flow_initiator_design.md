# FlowInitiator Design

**Status:** Design  
**Versie:** 1.0  
**Laatst Bijgewerkt:** 2025-11-04

---

## Executive Summary

FlowInitiator is een **per-strategy platform component** die verantwoordelijk is voor het initiëren van strategy pipeline runs. Het vormt een **symmetrisch paar** met FlowTerminator:

- **FlowInitiator**: Initialize run (cache.start_new_run) + trigger pipeline
- **FlowTerminator**: Cleanup run (cache.clear_cache) + persist causality

FlowInitiator lost het **race condition probleem** op waarbij workers de StrategyCache zouden kunnen lezen voordat deze geïnitialiseerd is, door een **twee-fase event flow** te introduceren met expliciete event namen.

---

## Problem Statement

### Het Race Condition Probleem

Zonder FlowInitiator zouden workers direct subscriben op externe events:

```yaml
# ❌ PROBLEEM: Race condition
signal_detector:
  subscriptions:
    - event_name: CANDLE_CLOSE_1H  # Direct van platform
```

```python
class SignalDetector:
    def process(self, candle: CandleCloseEvent):
        anchor = self._cache.get_run_anchor()  # 💥 NoActiveRunError!
        # RunAnchor bestaat nog niet - niemand heeft cache geïnitialiseerd
```

**Race condition:** Geen garantie dat cache geïnitialiseerd is voordat workers starten.

### Event Differentiatie Probleem

Strategieën moeten kunnen differentiëren tussen verschillende triggers:

```python
# Strategy luistert naar TWEE triggers:
# - CANDLE_CLOSE_1H → Opportunity evaluation
# - WEEKLY_SCHEDULE → Budget reset

# Maar hoe weet worker welk event hem triggerde?
```

Workers zijn **bus-agnostic** en kennen geen event namen, alleen connector IDs.

---

## Architecture Overview

### FlowInitiator in Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│ External Events (Platform Scope)                            │
│ - APL_CANDLE_CLOSE_1H (market data)                        │
│ - APL_WEEKLY_SCHEDULE (scheduler)                           │
│ - APL_NEWS_EVENT (news feed)                                │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ FlowInitiator (Per-Strategy Component)                      │
│                                                              │
│ Responsibilities:                                            │
│ 1. Initialize StrategyCache (start_new_run)                 │
│ 2. Filter events (should_start_flow)                        │
│ 3. Transform payload (APL_* → internal event)               │
│ 4. Publish READY events (via connector mapping)            │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ Internal Events (Strategy Scope)                            │
│ - CANDLE_CLOSE_1H (no APL_ prefix)                          │
│ - WEEKLY_SCHEDULE (no APL_ prefix)                          │
│ - NEWS_EVENT (no APL_ prefix)                               │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ Strategy Workers                                             │
│ - StrategyCache guaranteed to be initialized                │
│ - Event differentiatie via verschillende event namen        │
└─────────────────────────────────────────────────────────────┘
```

### Twee-Fase Event Flow

**Fase 1: External Event → FlowInitiator**
```
APL_CANDLE_CLOSE_1H event
    ↓
FlowInitiator.on_external_event()
    ├─ cache.start_new_run(timestamp)  ✅ RunAnchor created
    └─ return PUBLISH(candle_1h_ready, payload)
```

**Fase 2: FlowInitiator → Workers**
```
EventAdapter translates connector_id → event_name
    ↓
CANDLE_CLOSE_1H event (no APL_ prefix)
    ↓
SignalDetector.on_market_trigger()
    └─ cache.get_run_anchor() ✅ Exists!
```

**Event Naming Convention:**
- **Input events** (from application/platform): `APL_*` prefix (e.g., `APL_CANDLE_CLOSE_1H`)
- **Output events** (to strategy workers): No prefix, no suffix (e.g., `CANDLE_CLOSE_1H`)

---

## Component Design

### FlowInitiator Implementation

```python
# backend/core/flow_initiator.py

from datetime import datetime
from typing import Any
from backend.core.interfaces.worker import IWorker
from backend.core.interfaces.strategy_cache import IStrategyCache
from backend.dtos.shared.disposition_envelope import DispositionEnvelope, Disposition

class FlowInitiator(IWorker):
    """
    Generic flow initiator - configured via BuildSpec.
    
    Responsibilities:
    1. Initialize strategy run (StrategyCache.start_new_run)
    2. Filter external events (should_start_flow)
    3. Transform payload (external → internal DTO)
    4. Map input event → output connector (via BuildSpec config)
    
    Architecture Principles:
    - Bus-agnostic: Uses connector_ids, not event names
    - BuildSpec-driven: Configuration from strategy_blueprint.yaml
    - Per-strategy: One instance per strategy (like FlowTerminator)
    - Symmetry: start_new_run ↔ clear_cache (FlowTerminator)
    """
    
    def __init__(self, worker_id: str):
        """Initialize with worker ID."""
        self._worker_id = worker_id
        self._cache: IStrategyCache | None = None
        self._output_map: dict[str, str] = {}  # APL_* event_name → connector_id
    
    def configure(self, config: dict[str, Any], cache: IStrategyCache) -> None:
        """
        Configure with runtime config from WorkerBuildSpec.
        
        Args:
            config: Output mapping configuration
                {
                    "outputs": [
                        {"event_name": "APL_CANDLE_CLOSE_1H", "connector_id": "candle_1h_ready"},
                        {"event_name": "APL_SIGNAL_DETECTED", "connector_id": "signal_detected"}
                    ]
                }
            cache: StrategyCache instance
        """
        self._cache = cache
        
        # Build reverse mapping: APL_* event_name → connector_id
        for output in config.get("outputs", []):
            event_name = output["event_name"]
            connector_id = output["connector_id"]
            self._output_map[event_name] = connector_id
    
    def get_worker_id(self) -> str:
        """Return worker ID."""
        return self._worker_id
    
    def on_external_event(self, event: ExternalEvent) -> DispositionEnvelope:
        """
        Handle external trigger event (APL_* events).
        
        Flow:
        1. Initialize strategy run (side effect on cache)
        2. Lookup output connector from config
        3. Return PUBLISH disposition with mapped connector
        
        Args:
            event: External event with APL_* event_name, timestamp, payload
        
        Returns:
            DispositionEnvelope with PUBLISH disposition
        
        Raises:
            ValueError: If no output mapping configured for event
        """
        # 1. Initialize run (StrategyCache side effect)
        self._cache.start_new_run(
            strategy_cache={},  # Empty cache
            timestamp=event.timestamp
        )
        
        # 2. Lookup output connector from WorkerBuildSpec config
        output_connector = self._output_map.get(event.event_name)
        
        if output_connector is None:
            raise ValueError(
                f"FlowInitiator: No output mapping for event '{event.event_name}'. "
                f"Available mappings: {list(self._output_map.keys())}. "
                f"Check platform_components.flow_initiator.config in strategy_blueprint.yaml"
            )
        
        # 3. Return PUBLISH disposition (EventAdapter translates to event name without APL_ prefix)
        return DispositionEnvelope(
            disposition=Disposition.PUBLISH,
            connector_id=output_connector,
            payload=event.payload  # Forward original payload
        )
    
    def cleanup(self) -> None:
        """Cleanup resources (called at shutdown)."""
        pass
```

### BuildSpec Structure (IN-MEMORY)

FlowInitiator gebruikt de standaard **WorkerBuildSpec** Pydantic model (in-memory, niet on-disk):

```python
# IN-MEMORY BuildSpec generated by ConfigTranslator
# Validated against: backend/config/schemas/buildspecs/worker_build_spec_schema.py

WorkerBuildSpec(
    worker_id="flow_initiator",
    worker_type="FlowInitiator",
    config={
        "outputs": [
            {
                "event_name": "APL_CANDLE_CLOSE_1H",  # Input event (APL_ prefix)
                "connector_id": "candle_1h_ready"
            },
            {
                "event_name": "APL_WEEKLY_SCHEDULE",  # Input event (APL_ prefix)
                "connector_id": "weekly_ready"
            }
        ]
    }
)

# WorkerFactory receives this BuildSpec and:
# 1. Validates against worker_build_spec_schema.py
# 2. Instantiates FlowInitiator
# 3. Calls configure(config=buildspec.config, cache=strategy_cache)
```

---

## Configuration Architecture

### Strategy Blueprint (User Config)

```yaml
# strategy_blueprint.yaml
# Generated by Strategy Builder UI Canvas

metadata:
  strategy_id: "smart_dca_v1"
  version: "1.0.0"

# Platform components configuration
platform_components:
  flow_initiator:
    component_id: "platform/flow_initiator/v1.0.0"
    
    config:
      # Auto-generated by UI when user configures inputs
      inputs:
        - event_name: APL_CANDLE_CLOSE_1H    # Application event
          connector_id: candle_1h_ready
        - event_name: APL_WEEKLY_SCHEDULE    # Application event
          connector_id: weekly_ready
      
      # Auto-generated outputs (UI creates these when inputs are configured)
      outputs:
        - connector_id: candle_1h_ready
          event_name: CANDLE_CLOSE_1H      # No APL_ prefix, no _READY suffix
        - connector_id: weekly_ready
          event_name: WEEKLY_SCHEDULE      # No APL_ prefix, no _READY suffix
```

**Event Naming:**
- **Inputs**: `APL_*` prefix (application/platform events)
- **Outputs**: No prefix, no suffix (strategy-internal events)

### Strategy Wiring Map (Event Routing)

```yaml
# strategy_wiring_map.yaml
# Defines EventAdapter subscriptions/publications

adapter_configurations:
  flow_initiator:
    subscriptions:
      - event_name: APL_CANDLE_CLOSE_1H       # Subscribe to platform event
        connector_id: external_trigger
      - event_name: APL_WEEKLY_SCHEDULE       # Subscribe to platform event
        connector_id: external_trigger
    
    publications:
      - connector_id: candle_1h_ready
        event_name: CANDLE_CLOSE_1H         # Publish without APL_ prefix
      - connector_id: weekly_ready
        event_name: WEEKLY_SCHEDULE         # Publish without APL_ prefix

  signal_detector_1:
    subscriptions:
      - event_name: CANDLE_CLOSE_1H         # Subscribe to FlowInitiator output
        connector_id: market_trigger
      - event_name: WEEKLY_SCHEDULE         # Subscribe to FlowInitiator output
        connector_id: schedule_trigger
```

---

## API Service Layer

### FlowInitiatorConfigService

API service voor FlowInitiator metadata queries (read-only operations).

```python
# services/api_services/flow_initiator_config_service.py

from typing import List
from backend.config.manifest_loader import ManifestLoader

class FlowInitiatorConfigService:
    """
    API service providing FlowInitiator metadata to Strategy Builder UI.
    
    Responsibilities:
    - Query available platform event types (APL_* events)
    - Serve FlowInitiator manifest to UI
    - Basic validation of output configuration structure
    
    NOT responsible for:
    - BuildSpec generation (ConfigTranslator's job)
    - Schema validation (ConfigValidator's job)
    - Decision logic (ConfigTranslator's job)
    
    Layer: Service Layer (api_services subgroup)
    Consumers: BFF API endpoints (frontends/web/api/strategy_builder/)
    """
    
    def __init__(self):
        """Initialize service with manifest loader."""
        self._manifest_loader = ManifestLoader()
    
    def get_available_event_types(self) -> List[str]:
        """
        Query available platform event types for FlowInitiator inputs.
        
        Returns list of APL_* event names that can be configured.
        
        Returns:
            List of event names: ["APL_CANDLE_CLOSE_1H", "APL_SIGNAL_DETECTED", ...]
        """
        # Query from platform event registry or manifest
        return [
            "APL_CANDLE_CLOSE_1H",
            "APL_CANDLE_CLOSE_4H",
            "APL_CANDLE_CLOSE_1D",
            "APL_WEEKLY_SCHEDULE",
            "APL_DAILY_SCHEDULE",
            "APL_SIGNAL_DETECTED",
            "APL_RISK_EVENT",
            "APL_NEWS_EVENT"
        ]
    
    def get_manifest(self) -> dict:
        """
        Return FlowInitiator manifest for UI.
        
        UI uses manifest to:
        - Check capabilities.io.dynamic_outputs flag
        - Show platform component in UI
        - Understand dependencies
        
        Returns:
            Manifest dictionary with dynamic_outputs flag
        """
        return self._manifest_loader.load_manifest(
            "backend/config/manifests/flow_initiator_manifest.yaml"
        )
    
    def validate_output_config(self, outputs: List[dict]) -> bool:
        """
        Basic validation of output configuration structure.
        
        Simple validation only - complex validation in ConfigValidator.
        
        Args:
            outputs: List of output configurations
                [
                    {"event_name": "APL_CANDLE_CLOSE_1H", "connector_id": "candle_1h_ready"},
                    ...
                ]
        
        Returns:
            True if structure is valid
        
        Raises:
            ValueError: If structure is invalid
        """
        for output in outputs:
            if "event_name" not in output or "connector_id" not in output:
                raise ValueError("Output must have 'event_name' and 'connector_id'")
            
            # Check APL_ prefix
            if not output["event_name"].startswith("APL_"):
                raise ValueError(
                    f"Input event must have APL_ prefix: {output['event_name']}"
                )
        
        return True
```

---

## BFF API Layer

### FlowInitiator Endpoints

Backend-for-Frontend API endpoints voor Strategy Builder UI.

```python
# frontends/web/api/strategy_builder/flow_initiator_endpoints.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from services.api_services.flow_initiator_config_service import FlowInitiatorConfigService

router = APIRouter(
    prefix="/api/strategy-builder/flow-initiator",
    tags=["strategy-builder"]
)

# Initialize API service
config_service = FlowInitiatorConfigService()

class AvailableEventsResponse(BaseModel):
    """Response model for available platform events."""
    events: List[str]

class ManifestResponse(BaseModel):
    """Response model for FlowInitiator manifest."""
    manifest: dict

@router.get("/available-events", response_model=AvailableEventsResponse)
def get_available_platform_events():
    """
    Query: Get available platform event types (APL_* events).
    
    Used by Strategy Builder UI to populate dropdown in Platform Components step.
    
    Returns:
        List of APL_* event names that can be configured as FlowInitiator inputs
    """
    events = config_service.get_available_event_types()
    return AvailableEventsResponse(events=events)

@router.get("/manifest", response_model=ManifestResponse)
def get_flow_initiator_manifest():
    """
    Query: Get FlowInitiator manifest.
    
    Used by Strategy Builder UI to:
    - Check capabilities.io.dynamic_outputs flag
    - Show platform component metadata
    - Understand dependencies
    
    Returns:
        FlowInitiator manifest dictionary
    """
    manifest = config_service.get_manifest()
    return ManifestResponse(manifest=manifest)
    service = FlowInitiatorConfigService()
    current_config = blueprint["platform_components"]["flow_initiator"]["config"]
    
    updated_config = service.add_trigger(
        current_config,
        request.trigger_event
    )
    
    # Update blueprint
    blueprint["platform_components"]["flow_initiator"]["config"] = updated_config
    save_strategy_blueprint(request.strategy_id, blueprint)
    
    return {
        "flowInitiatorConfig": updated_config,
        "newOutputs": service.get_available_outputs(updated_config)
    }

@router.post("/remove-trigger")
def remove_trigger_from_flow_initiator(request: RemoveTriggerRequest):
    """Command: Remove trigger from FlowInitiator."""
    blueprint = load_strategy_blueprint(request.strategy_id)
    service = FlowInitiatorConfigService()
    
    current_config = blueprint["platform_components"]["flow_initiator"]["config"]
    updated_config = service.remove_trigger(current_config, request.trigger_event)
    
    blueprint["platform_components"]["flow_initiator"]["config"] = updated_config
    save_strategy_blueprint(request.strategy_id, blueprint)
    
    return {
        "flowInitiatorConfig": updated_config
    }

@router.get("/outputs")
def get_flow_initiator_outputs(strategy_id: str):
    """
    Query: Get available FlowInitiator outputs for wiring.
    
    Used by UI to display available connectors.
    """
    blueprint = load_strategy_blueprint(strategy_id)
    service = FlowInitiatorConfigService()
    
    config = blueprint["platform_components"]["flow_initiator"]["config"]
    
    return {
        "outputs": service.get_available_outputs(config)
    }
```

---

## UI Integration

### Strategy Builder UI Flow

**Step 1: User Adds Data Connector**

```typescript
// frontend/strategy-builder/controllers/canvas.controller.ts

class CanvasController {
  async addDataConnector(connectorType: string) {
    // Call backend command service
    const response = await this.api.post('/strategy-builder/flow-initiator/add-trigger', {
      strategyId: this.currentStrategy.id,
      triggerEvent: connectorType.toUpperCase()
    });
    
    // Backend returns updated config
    const updatedConfig = response.data.flowInitiatorConfig;
    const newOutputs = response.data.newOutputs;
    
    // Update local blueprint
    this.strategyBlueprint.platformComponents.flowInitiator.config = updatedConfig;
    
    // Update canvas (show new output port on FlowInitiator)
    this.flowInitiatorNode.addOutputPorts(newOutputs);
    
    // Show notification
    this.notificationService.success(
      `Added ${connectorType} trigger to FlowInitiator`
    );
  }
  
  async removeDataConnector(connectorType: string) {
    // Validate: Check if any workers are wired to this output
    const outputEvent = connectorType.toUpperCase() + "_READY";
    const hasConnections = this.canvasService.hasConnectionsToEvent(outputEvent);
    
    if (hasConnections) {
      const confirm = await this.dialogService.confirm(
        'Remove Trigger',
        `This trigger is connected to workers. Removing it will break those connections. Continue?`
      );
      
      if (!confirm) return;
    }
    
    // Call backend
    await this.api.post('/strategy-builder/flow-initiator/remove-trigger', {
      strategyId: this.currentStrategy.id,
      triggerEvent: connectorType.toUpperCase()
    });
    
    // Update UI
    this.flowInitiatorNode.removeOutputPort(outputEvent);
  }
}
```

**Step 2: User Wires FlowInitiator to Workers**

```typescript
class WiringController {
  createConnection(
    sourceNode: string,
    sourcePort: string,
    targetNode: string,
    targetPort: string
  ) {
    // Validate connection
    if (sourceNode === 'flow_initiator') {
      // FlowInitiator output port names ARE the event names
      const eventName = sourcePort;  // e.g., "CANDLE_CLOSE_1H_READY"
      
      // Add to wiring map
      this.wiringMap.addSubscription(targetNode, {
        event_name: eventName,
        connector_id: targetPort
      });
    }
    
    // Update canvas
    this.canvasService.drawConnection(sourceNode, sourcePort, targetNode, targetPort);
  }
}
```

---

## Config Translation Flow

### ConfigTranslator

```python
# backend/assembly/config_translator.py

class ConfigTranslator:
    """
    Translates YAML configs to BuildSpecs.
    
    Uniform for all components (workers and platform components).
    """
    
    def translate_platform_component(
        self,
        component_config: dict,
        strategy_cache: IStrategyCache
    ) -> ComponentBuildSpec:
        """
        Translate platform component config to BuildSpec.
        
        Args:
            component_config: Config from strategy_blueprint.yaml
            strategy_cache: Per-strategy cache instance
        
        Returns:
            ComponentBuildSpec (FlowInitiatorBuildSpec for flow_initiator)
        """
        component_id = component_config["component_id"]
        
        if component_id.startswith("platform/flow_initiator"):
            # FlowInitiator BuildSpec
            return FlowInitiatorBuildSpec(
                component_id=component_id,
                worker_id=self._generate_worker_id("flow_initiator"),
                strategy_cache=strategy_cache,
                config=component_config["config"]  # Direct from blueprint
            )
        elif component_id.startswith("platform/flow_terminator"):
            # FlowTerminator BuildSpec
            return FlowTerminatorBuildSpec(...)
        else:
            raise ValueError(f"Unknown platform component: {component_id}")
```

---

## Runtime Flow

### Bootstrap Sequence

```python
# backend/assembly/bootstrap.py

class StrategyBootstrap:
    """Bootstrap strategy runtime from configs."""
    
    def bootstrap_strategy(
        self,
        strategy_blueprint: dict,
        strategy_wiring: dict
    ) -> StrategyRuntime:
        """
        Bootstrap complete strategy runtime.
        
        Flow:
        1. Create per-strategy StrategyCache
        2. Translate configs to BuildSpecs (ConfigTranslator)
        3. Create components (WorkerFactory)
        4. Wire events (EventWiringFactory)
        """
        # 1. Create per-strategy cache
        strategy_cache = StrategyCache()
        
        # 2. Translate platform components
        translator = ConfigTranslator()
        platform_components = {}
        
        for comp_name, comp_config in strategy_blueprint["platform_components"].items():
            build_spec = translator.translate_platform_component(
                comp_config,
                strategy_cache
            )
            platform_components[comp_name] = build_spec
        
        # 3. Create components via WorkerFactory
        factory = WorkerFactory()
        flow_initiator = factory.create_platform_component(
            platform_components["flow_initiator"]
        )
        
        # 4. Create EventAdapter for FlowInitiator
        wiring_factory = EventWiringFactory()
        flow_initiator_adapter = wiring_factory.create_adapter(
            worker=flow_initiator,
            adapter_config=strategy_wiring["adapter_configurations"]["flow_initiator"],
            event_bus=self.event_bus
        )
        
        # 5. Register adapter with EventBus
        for subscription in flow_initiator_adapter.subscriptions:
            self.event_bus.subscribe(
                event_name=subscription.event_name,
                handler=flow_initiator_adapter.on_event,
                scope=subscription.scope
            )
        
        return StrategyRuntime(
            strategy_id=strategy_blueprint["metadata"]["strategy_id"],
            components=[flow_initiator, ...],
            adapters=[flow_initiator_adapter, ...]
        )
```

### Event Flow at Runtime

```
1. Platform publishes: CANDLE_CLOSE_1H
   Payload: CandleCloseEvent(timestamp=..., close=50000, ...)
   Scope: PLATFORM
   
2. EventBus routes to subscribers
   ├─ FlowInitiator (strategy STR_ABC has subscription)
   └─ Other strategies also subscribed (if configured)

3. FlowInitiator EventAdapter receives event
   ├─ Matches subscription: CANDLE_CLOSE_1H → external_trigger
   └─ Calls: flow_initiator.on_external_event(event)

4. FlowInitiator.on_external_event()
   ├─ cache.start_new_run({}, event.timestamp)  ✅ RunAnchor created
   └─ return PUBLISH(connector_id="candle_1h_ready", payload=event.payload)

5. EventAdapter handles PUBLISH disposition
   ├─ Lookup publication: candle_1h_ready → CANDLE_CLOSE_1H_READY
   └─ event_bus.publish("CANDLE_CLOSE_1H_READY", payload, scope=STRATEGY)

6. Workers receive CANDLE_CLOSE_1H_READY (strategy scope)
   └─ SignalDetector.on_market_trigger(payload)
        └─ cache.get_run_anchor() ✅ Exists!
```

---

## Design Principles

### 1. Symmetry with FlowTerminator

```python
# BEGIN: FlowInitiator
flow_initiator.on_external_event(event)
    └─ cache.start_new_run(timestamp)

# END: FlowTerminator
flow_terminator.on_execution_complete(directive)
    └─ cache.clear_cache()
```

### 2. Tight Coupling is Correct

FlowInitiator ↔ StrategyCache coupling is **essentieel** en **expliciet**:
- ✅ FlowInitiator MOET cache initialiseren (naam = verantwoordelijkheid)
- ✅ Dit is lifecycle management, geen business logic
- ✅ Symmetrie met FlowTerminator rechtvaardigt dit

### 3. Bus-Agnostic Architecture

FlowInitiator blijft bus-agnostic:
- ✅ Gebruikt `connector_id`, niet `event_name`
- ✅ EventAdapter doet vertaling
- ✅ BuildSpec bevat mapping (geen hard-coded event names)

### 4. Backend Domain Logic

Configuratie logic in backend, niet UI:
- ✅ FlowInitiatorConfigService beheert naming conventions
- ✅ Command/Query pattern voor UI interactie
- ✅ Validatie in backend
- ✅ UI blijft "dumb" (rendering + user input)

### 5. Single Source of Truth

strategy_blueprint.yaml bevat alle configuratie:
- ✅ FlowInitiator config (trigger_mappings, inputs, outputs)
- ✅ Worker configs
- ✅ Geen separate config files

### 6. Uniform Config Flow

FlowInitiator volgt zelfde pattern als alle components:
```
strategy_blueprint.yaml
    ↓
ConfigTranslator
    ↓
FlowInitiatorBuildSpec
    ↓
WorkerFactory
    ↓
FlowInitiator.initialize(BuildSpec)
```

---

## Naming Conventions

### Event Naming Pattern

**External Event → Internal Event:**
```
CANDLE_CLOSE_1H → CANDLE_CLOSE_1H_READY
WEEKLY_SCHEDULE → WEEKLY_SCHEDULE_READY
NEWS_EVENT      → NEWS_EVENT_READY
```

**Pattern:** `{EXTERNAL_EVENT}_READY`

### Connector Naming Pattern

**Event → Connector ID:**
```
CANDLE_CLOSE_1H → candle_1h_ready
WEEKLY_SCHEDULE → weekly_ready
NEWS_EVENT      → news_event_ready
```

**Pattern:** `lowercase({EVENT_NAME})_ready`

### Code Location

```python
# Naming convention logic
class FlowInitiatorConfigService:
    def _derive_output_connector(self, event_name: str) -> str:
        """CANDLE_CLOSE_1H → candle_1h_ready"""
        return event_name.lower() + "_ready"
    
    def _derive_output_event(self, event_name: str) -> str:
        """CANDLE_CLOSE_1H → CANDLE_CLOSE_1H_READY"""
        return event_name + "_READY"
```

**Convention Location:** Backend service (single source of truth)

---

## Worker Implementation Examples

### Worker Met Multiple Triggers

```python
# Plugin worker dat op BEIDE triggers reageert

class SignalDetector(StandardWorker):
    """
    Manifest definieert twee input connectors:
    - market_trigger (voor CANDLE_CLOSE_1H_READY)
    - schedule_trigger (voor WEEKLY_SCHEDULE_READY)
    """
    
    def on_market_trigger(self, candle: CandleCloseEvent) -> DispositionEnvelope:
        """Handler for market tick events."""
        anchor = self._cache.get_run_anchor()  # ✅ Guaranteed to exist
        
        # Opportunity evaluation logic
        opportunity = self._evaluate_opportunity(candle, anchor.timestamp)
        
        if opportunity:
            return DispositionEnvelope(
                disposition=Disposition.PUBLISH,
                connector_id="opportunity_detected",
                payload=OpportunitySignal(...)
            )
        
        return DispositionEnvelope(
            disposition=Disposition.CONTINUE,
            connector_id="completion"
        )
    
    def on_schedule_trigger(self, schedule: ScheduleTickEvent) -> DispositionEnvelope:
        """Handler for scheduled events."""
        anchor = self._cache.get_run_anchor()  # ✅ Guaranteed to exist
        
        # Budget reset logic
        self._reset_budget(schedule, anchor.timestamp)
        
        return DispositionEnvelope(
            disposition=Disposition.CONTINUE,
            connector_id="completion"
        )
```

### Wiring

```yaml
# strategy_wiring_map.yaml

signal_detector_1:
  subscriptions:
    - event_name: CANDLE_CLOSE_1H_READY
      connector_id: market_trigger     # → on_market_trigger()
    
    - event_name: WEEKLY_SCHEDULE_READY
      connector_id: schedule_trigger   # → on_schedule_trigger()
  
  publications:
    - connector_id: opportunity_detected
      event_name: OPPORTUNITY_DETECTED
    
    - connector_id: completion
      event_name: SIGNAL_DETECTION_COMPLETE
```

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/core/test_flow_initiator.py

class TestFlowInitiator:
    """Unit tests for FlowInitiator."""
    
    def test_initialize_from_buildspec(self):
        """Test initialization with BuildSpec."""
        cache = Mock(spec=IStrategyCache)
        build_spec = FlowInitiatorBuildSpec(
            component_id="platform/flow_initiator/v1.0.0",
            worker_id="flow_initiator_test",
            strategy_cache=cache,
            config={
                "trigger_mappings": {
                    "CANDLE_CLOSE_1H": "candle_1h_ready",
                    "WEEKLY_SCHEDULE": "weekly_ready"
                }
            }
        )
        
        initiator = FlowInitiator("flow_initiator_test")
        initiator.initialize(build_spec)
        
        assert initiator._cache is cache
        assert initiator._trigger_mappings == {
            "CANDLE_CLOSE_1H": "candle_1h_ready",
            "WEEKLY_SCHEDULE": "weekly_ready"
        }
    
    def test_on_external_event_initializes_cache(self):
        """Test that on_external_event calls cache.start_new_run."""
        cache = Mock(spec=IStrategyCache)
        initiator = self._create_initiator(cache)
        
        event = ExternalEvent(
            event_name="CANDLE_CLOSE_1H",
            timestamp=datetime.now(timezone.utc),
            payload=CandleCloseEvent(...)
        )
        
        envelope = initiator.on_external_event(event)
        
        # Verify cache initialized
        cache.start_new_run.assert_called_once_with({}, event.timestamp)
        
        # Verify correct output connector
        assert envelope.disposition == Disposition.PUBLISH
        assert envelope.connector_id == "candle_1h_ready"
        assert envelope.payload == event.payload
    
    def test_on_external_event_unknown_trigger_raises(self):
        """Test that unknown event raises ValueError."""
        cache = Mock(spec=IStrategyCache)
        initiator = self._create_initiator(cache)
        
        event = ExternalEvent(
            event_name="UNKNOWN_EVENT",
            timestamp=datetime.now(timezone.utc),
            payload={}
        )
        
        with pytest.raises(ValueError, match="No output mapping"):
            initiator.on_external_event(event)
```

### Integration Tests

```python
# tests/integration/test_flow_initiator_integration.py

class TestFlowInitiatorIntegration:
    """Integration tests with EventBus and StrategyCache."""
    
    def test_complete_flow_with_workers(self):
        """Test complete flow: External event → FlowInitiator → Workers."""
        # Setup
        event_bus = EventBus()
        cache = StrategyCache()
        
        # Bootstrap FlowInitiator
        flow_initiator = self._bootstrap_flow_initiator(cache)
        flow_adapter = self._create_adapter(flow_initiator, event_bus)
        
        # Bootstrap Worker
        worker = SignalDetector("detector_1")
        worker_adapter = self._create_adapter(worker, event_bus)
        
        # Track worker calls
        worker_called = Mock()
        original_process = worker.on_market_trigger
        worker.on_market_trigger = lambda e: (worker_called(), original_process(e))
        
        # Publish external event
        event_bus.publish(
            "CANDLE_CLOSE_1H",
            CandleCloseEvent(...),
            scope=ScopeLevel.PLATFORM
        )
        
        # Verify flow
        assert cache.get_run_anchor() is not None  # Cache initialized
        worker_called.assert_called_once()  # Worker received READY event
```

### Service Tests

```python
# tests/unit/assembly/services/test_flow_initiator_config_service.py

class TestFlowInitiatorConfigService:
    """Test FlowInitiatorConfigService."""
    
    def test_add_trigger_generates_correct_mapping(self):
        """Test add_trigger creates correct connector mapping."""
        service = FlowInitiatorConfigService()
        
        config = {
            "trigger_mappings": {},
            "inputs": [],
            "outputs": []
        }
        
        updated = service.add_trigger(config, "CANDLE_CLOSE_1H")
        
        # Verify mapping
        assert updated["trigger_mappings"]["CANDLE_CLOSE_1H"] == "candle_1h_ready"
        
        # Verify input
        assert len(updated["inputs"]) == 1
        assert updated["inputs"][0]["connector_id"] == "external_trigger"
        assert "CANDLE_CLOSE_1H" in updated["inputs"][0]["event_types"]
        
        # Verify output
        assert len(updated["outputs"]) == 1
        assert updated["outputs"][0]["connector_id"] == "candle_1h_ready"
        assert updated["outputs"][0]["event_name"] == "CANDLE_CLOSE_1H_READY"
    
    def test_naming_conventions(self):
        """Test naming convention methods."""
        service = FlowInitiatorConfigService()
        
        assert service._derive_output_connector("CANDLE_CLOSE_1H") == "candle_1h_ready"
        assert service._derive_output_connector("WEEKLY_SCHEDULE") == "weekly_schedule_ready"
        
        assert service._derive_output_event("CANDLE_CLOSE_1H") == "CANDLE_CLOSE_1H_READY"
        assert service._derive_output_event("WEEKLY_SCHEDULE") == "WEEKLY_SCHEDULE_READY"
```

---

## Platform Component Manifest

**Complete manifest design:** See [FlowInitiator Manifest Design](FLOW_INITIATOR_MANIFEST.md)

### Key Manifest Properties

```yaml
# backend/config/manifests/flow_initiator_manifest.yaml

plugin_id: "platform/flow_initiator/v1.0.0"
category: "platform_component"

capabilities:
  io:
    dynamic_outputs: true    # 🔥 Outputs from strategy_blueprint, not manifest

dependencies:
  requires_system_resources:
    strategy_cache: true

inputs:
  - connector_id: "external_trigger"
    handler_method: "on_external_event"

outputs: []  # Empty - runtime generated
```

**Event Naming Convention:**
- **Inputs:** `APL_*` prefix (e.g., `APL_CANDLE_CLOSE_1H`)
- **Outputs:** No prefix, no suffix (e.g., `CANDLE_CLOSE_1H`)

**Manifest Location:**
- Platform manifests: `backend/config/manifests/`
- Plugin manifests: `plugins/workers/{category}/{name}/manifest.yaml`

---

## Component Positioning (3-Layer Architecture)

### Backend Layer (Layer 3: Engine)
```
backend/
├── core/
│   └── flow_initiator.py                    # FlowInitiator implementation
├── assembly/
│   ├── config_translator.py                 # IN-MEMORY BuildSpec generation
│   ├── worker_factory.py                    # Worker instantiation
│   └── event_wiring_factory.py              # EventAdapter wiring
├── config/
│   ├── manifests/
│   │   └── flow_initiator_manifest.yaml     # Platform manifest
│   └── schemas/
│       └── buildspecs/
│           ├── worker_build_spec_schema.py  # BuildSpec validation schema
│           └── wiring_build_spec_schema.py  # WiringBuildSpec validation schema
└── dtos/
```

### Service Layer (Layer 2: Orchestration)
```
services/
├── operation_service.py                     # Domain service: lifecycle
├── optimization_service.py                  # Domain service: workflows
└── api_services/
    └── flow_initiator_config_service.py     # API service: metadata queries
```

### Frontend Layer (Layer 1: Presentation)
```
frontends/
└── web/
    ├── api/ (BFF - Backend-for-Frontend)
    │   └── strategy_builder/
    │       └── flow_initiator_endpoints.py  # REST endpoints
    └── ui/
        └── components/
            └── PlatformComponentsStep.tsx   # UI component
```

**Key Principles:**
- **ConfigTranslator** = "THE THINKER" (all decision logic)
- **Factories** = "PURE BUILDERS" (no decisions, only assembly)
- **BuildSpecs** = IN-MEMORY only (validated against schemas, not stored on disk)
- **API Services** = Read-only metadata queries for UI
- **BFF API** = Backend-for-Frontend REST endpoints

---

## Implementation Components

### Core Components (Backend Layer)
- `backend/core/flow_initiator.py` - FlowInitiator implementation
- `backend/config/manifests/flow_initiator_manifest.yaml` - Platform manifest
- `backend/config/schemas/buildspecs/worker_build_spec_schema.py` - Validation schema

### Service Components (Service Layer)
- `services/api_services/flow_initiator_config_service.py` - API service for metadata

### Config Integration (Backend Layer)
- ConfigTranslator FlowInitiator support (IN-MEMORY WorkerBuildSpec generation)
- WorkerFactory FlowInitiator instantiation
- EventWiringFactory adapter creation (IN-MEMORY WiringBuildSpecs)

### Frontend API (Frontend Layer)
- `frontends/web/api/strategy_builder/flow_initiator_endpoints.py` - BFF REST endpoints
- Request/Response DTOs

### UI Integration (Frontend Layer)
- Canvas FlowInitiator node (dynamic outputs from strategy_blueprint)
- Platform Components configuration UI
- Auto-generated outputs when inputs configured
- Output connector rendering

---

## Related Documentation

- **Manifest Design:** [FlowInitiator Manifest](FLOW_INITIATOR_MANIFEST.md)
- **Architecture:** [Platform Components](../../../architecture/PLATFORM_COMPONENTS.md)
- **Architecture:** [Event-Driven Wiring](../../../architecture/EVENT_DRIVEN_WIRING.md)
- **Reference:** [StrategyCache](../../../reference/platform/strategy_cache.md)


