# FlowInitiator Manifest Design

**Onderdeel van:** [FlowInitiator Design](flow_initiator_design.md)  
**Status:** Design  
**Laatst Bijgewerkt:** 2025-11-04

---

## Manifest Location

Platform component manifests are stored in:
```
backend/config/manifests/flow_initiator_manifest.yaml
```

**Note:** Plugin manifests are stored differently:
```
plugins/workers/{category}/{name}/manifest.yaml
```

Only platform components use `backend/config/manifests/`.

---

## Complete Manifest Structure

```yaml
# backend/config/manifests/flow_initiator_manifest.yaml

plugin_id: "platform/flow_initiator/v1.0.0"
plugin_type: "worker"
category: "platform_component"

metadata:
  name: "Flow Initiator"
  description: "Platform component managing strategy initialization and external event coordination"
  author: "S1mpleTrader Platform"
  version: "1.0.0"

scope_behavior:
  subscription_mode: "strategy"
  publication_scope: "strategy"

capabilities:
  io:
    multi_input: true
    broadcast_output: true
    dynamic_outputs: true    # 🔥 KEY FLAG: Outputs from strategy_blueprint, not manifest

dependencies:
  requires_system_resources:
    strategy_cache: true

inputs:
  - connector_id: "external_trigger"
    handler_method: "on_external_event"

outputs: []  # Empty - populated at runtime from strategy_blueprint.yaml
```

---

## Key Manifest Properties

### Category: `platform_component`

Marks this as platform component, not user plugin:
- UI shows in separate "Platform Components" section
- WorkerFactory handles differently (pre-configured, not from plugin registry)
- Special bootstrap handling

### Capabilities

**`dynamic_outputs: true`** - **Critical for UI behavior:**
- UI knows: "Don't read outputs from manifest"
- UI knows: "Read outputs from strategy_blueprint.platform_components.flow_initiator.config"
- Canvas refresh pulls outputs from in-memory strategy_blueprint

**`multi_input: true`:**
- Accepts multiple different APL_* event types on same connector
- FlowInitiator can handle different events via single `external_trigger` connector

**`broadcast_output: true`:**
- Outputs available to all workers in strategy
- No isolation - any worker can subscribe to FlowInitiator outputs

### Dependencies

**`requires_system_resources.strategy_cache: true`:**
- Indicates FlowInitiator needs StrategyCache injection
- WorkerFactory ensures cache is injected during `configure()`

### Inputs

**Single connector: `external_trigger`:**
- No `event_type` in manifest (that's runtime info from strategy_blueprint)
- Handler: `on_external_event()` method
- Accepts all APL_* events configured in strategy_blueprint

### Outputs

**Empty list in manifest:**
- Runtime outputs come from `strategy_blueprint.yaml`:
  ```yaml
  platform_components:
    flow_initiator:
      config:
        outputs:
          - connector_id: candle_1h_ready
            event_name: CANDLE_CLOSE_1H          # No APL_ prefix, no _READY suffix
          - connector_id: signal_detected
            event_name: SIGNAL_DETECTED          # No APL_ prefix, no _READY suffix
  ```

---

## Event Naming Convention

### Input Events (APL_* prefix)

**Application/Platform events** have `APL_` prefix:
```
APL_CANDLE_CLOSE_1H
APL_WEEKLY_SCHEDULE
APL_SIGNAL_DETECTED
APL_RISK_EVENT
```

**Purpose:**
- Immediately distinguishable as application-level events
- Clear boundary between platform and strategy scopes
- Prevents naming collisions

### Output Events (no prefix, no suffix)

**Strategy-internal events** have no APL_ prefix and no _READY suffix:
```
CANDLE_CLOSE_1H
WEEKLY_SCHEDULE
SIGNAL_DETECTED
RISK_EVENT
```

**Pattern:** Strip `APL_` prefix (no additional suffix)

**Transformation:**
```
APL_CANDLE_CLOSE_1H  →  CANDLE_CLOSE_1H
APL_WEEKLY_SCHEDULE  →  WEEKLY_SCHEDULE
APL_SIGNAL_DETECTED  →  SIGNAL_DETECTED
```

---

## Manifest vs Normal Plugin

### Normal Plugin (Static Outputs)

```yaml
# plugins/workers/signal_detector_manifest.yaml

plugin_id: "workers/signal/momentum_detector/v1.0.0"
category: "signal"

inputs:
  - connector_id: "market_data"
    handler_method: "process_candle"

outputs:  # ✅ Static - always the same
  - connector_id: "signal_detected"
  - connector_id: "no_signal"
  - connector_id: "error"
```

**Characteristics:**
- Outputs are **static** (defined in manifest)
- UI reads outputs from manifest
- Outputs never change based on configuration

### FlowInitiator (Dynamic Outputs)

```yaml
# backend/config/manifests/flow_initiator_manifest.yaml

plugin_id: "platform/flow_initiator/v1.0.0"
category: "platform_component"

capabilities:
  io:
    dynamic_outputs: true  # 🔥 Flag for UI

inputs:
  - connector_id: "external_trigger"

outputs: []  # 🔥 Empty - runtime generated
```

**Characteristics:**
- Outputs are **dynamic** (generated based on inputs)
- UI reads outputs from strategy_blueprint
- Outputs change when user configures different inputs

---

## Manifest Usage Flow

### Design Time (Strategy Builder UI)

```
1. UI loads FlowInitiator manifest
   GET /api/strategy-builder/flow-initiator/manifest
   
2. UI checks: capabilities.io.dynamic_outputs === true
   → Knows to read outputs from strategy_blueprint
   
3. User configures inputs in Platform Components step
   Input: APL_CANDLE_CLOSE_1H
   
4. UI auto-generates output in strategy_blueprint
   Output: CANDLE_CLOSE_1H (connector: candle_1h_ready)
   
5. Canvas refreshes FlowInitiator node
   → Reads outputs from strategy_blueprint.platform_components.flow_initiator.config
   → Shows output connector: candle_1h_ready
   
6. User wires FlowInitiator.candle_1h_ready → SignalDetector.market_trigger
```

### Runtime (Bootstrap)

```
1. ConfigTranslator reads strategy_blueprint.yaml
   
2. ConfigTranslator generates IN-MEMORY WorkerBuildSpec:
   WorkerBuildSpec(
     worker_id="flow_initiator",
     config={
       "outputs": [
         {"event_name": "APL_CANDLE_CLOSE_1H", "connector_id": "candle_1h_ready"}
       ]
     }
   )
   
3. WorkerFactory validates BuildSpec against schema
   backend/config/schemas/buildspecs/worker_build_spec_schema.py
   
4. WorkerFactory instantiates FlowInitiator
   flow_initiator.configure(config, strategy_cache)
   
5. FlowInitiator builds internal mapping:
   self._output_map["APL_CANDLE_CLOSE_1H"] = "candle_1h_ready"
   
6. Runtime: APL_CANDLE_CLOSE_1H event arrives
   → FlowInitiator.on_external_event()
   → Returns PUBLISH(connector_id="candle_1h_ready")
   → EventAdapter publishes CANDLE_CLOSE_1H (no APL_ prefix, no _READY suffix)
```

---

## Who Uses the Manifest?

| Component | Uses Manifest? | Purpose |
|-----------|---------------|---------|
| Strategy Builder UI | ✅ YES | Check `dynamic_outputs` flag, show platform component |
| FlowInitiatorConfigService | ✅ YES | Serve manifest to BFF API |
| WorkerFactory | ❌ NO | Uses WorkerBuildSpec from ConfigTranslator |
| EventWiringFactory | ❌ NO | Uses WiringBuildSpecs from strategy_wiring_map |
| ConfigTranslator | ✅ YES (optional) | Read manifest for metadata |
| FlowInitiator (worker) | ❌ NO | Receives config via WorkerBuildSpec |

---

## When Is Manifest Used?

**✅ Design Time:**
- UI queries manifest to build Strategy Builder interface
- UI checks `dynamic_outputs` flag
- UI shows platform component in correct section

**❌ Runtime:**
- Bootstrap uses WorkerBuildSpecs, NOT manifests
- EventWiringFactory uses WiringBuildSpecs
- Workers receive config via BuildSpec, not manifest

---

**Last Updated:** 2025-11-04
