# FlowInitiator Manifest Design

**Onderdeel van:** [FlowInitiator Design](FLOW_INITIATOR_DESIGN.md)  
**Status:** Design  
**Laatst Bijgewerkt:** 2025-11-06

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
  description: "Per-strategy data ingestion and cache initialization component"
  author: "S1mpleTrader Platform"
  version: "1.0.0"

scope_behavior:
  subscription_mode: "strategy"
  publication_scope: "strategy"

capabilities:
  io:
    multi_input: true
    broadcast_output: true
    dynamic_outputs: false    # 🔥 Changed: Outputs are EMPTY, no dynamic generation

dependencies:
  requires_system_resources:
    strategy_cache: true

inputs:
  - connector_id: "data_input"
    handler_method: "on_data_ready"    # 🔥 Changed: Single handler for all data types

outputs: []  # Empty - EventAdapter publication_on_continue handles routing
```

**Key Changes from V1:**
- ✅ Handler method: `on_data_ready` (not `on_external_event`)
- ✅ Connector: `data_input` (generic, not `external_trigger`)
- ✅ `dynamic_outputs: false` - No runtime output generation
- ✅ Empty `outputs` - EventAdapter `publication_on_continue` handles routing

---

## Key Manifest Properties

### Category: `platform_component`

Marks this as platform component, not user plugin:
- UI shows in separate "Platform Components" section
- WorkerFactory handles differently (pre-configured, not from plugin registry)
- Special bootstrap handling

### Capabilities

**`dynamic_outputs: false`** - **No runtime output generation:**
- FlowInitiator has NO outputs in manifest (empty list)
- EventAdapter uses `publication_on_continue` for routing
- See [EventAdapter Design](../EVENTADAPTER_DESIGN.md#publication_on_continue) for details

**`multi_input: true`:**
- Accepts multiple different data types on same connector
- FlowInitiator can handle candles, news, orderbook, etc. via single `data_input` connector
- Single handler method (`on_data_ready`) processes all types

**`broadcast_output: true`:**
- Events published via `publication_on_continue` available to all workers
- No isolation - any worker can subscribe to data events

### Dependencies

**`requires_system_resources.strategy_cache: true`:**
- Indicates FlowInitiator needs StrategyCache injection
- WorkerFactory ensures cache is injected during `configure()`

### Inputs

**Single connector: `data_input`:**
- Generic handler for ALL data types (candles, news, orderbook, etc.)
- Handler: `on_data_ready()` method
- Receives PlatformDataDTO from DataProviders
- See [DataProvider Design](DATA_PROVIDER_DESIGN.md) for PlatformDataDTO structure

### Outputs

**Empty list in manifest:**
- FlowInitiator has NO outputs declared in manifest
- Event routing handled by EventAdapter `publication_on_continue` mechanism
- Wiring map example:
  ```yaml
  flow_initiator:
    subscriptions:
      - event_name: "_candle_btc_eth_ready_strategy_abc"
        connector_id: "data_input"
        handler_method: "on_data_ready"  # From manifest
        publication_on_continue: "candle_stream_ready"  # EventAdapter routes here
    
    publications:
      - connector_id: "candle_stream_ready"
        event_name: "CANDLE_STREAM_DATA_READY"
  ```
- See [FlowInitiator Design](FLOW_INITIATOR_DESIGN.md#eventadapter-wiring) for complete wiring pattern

---

## Event Naming Convention

### Input Events (Provider Events)

**DataProvider events** have provider-specific naming with strategy_id suffix:
```
_candle_btc_eth_ready_{strategy_id}
_orderbook_binance_ready_{strategy_id}
_bloomberg_news_ready_{strategy_id}
```

**Pattern:** `_{provider_id}_ready_{strategy_id}`

**Purpose:**
- Strategy-scoped delivery (only relevant strategy receives event)
- Multiple strategies can share same DataProvider (singleton)
- Provider ID identifies data source

### Output Events (Worker Events)

**Worker-facing events** are uppercase strategy-internal events:
```
CANDLE_STREAM_DATA_READY
ORDERBOOK_SNAPSHOT_READY
NEWS_FEED_DATA_READY
```

**Pattern:** `{DATA_TYPE}_READY` (uppercase, descriptive)

**Purpose:**
- Clear boundary: external provider events → internal worker events
- Workers don't know about provider IDs
- Clean abstraction layer

**Transformation Flow:**
```
DataProvider publishes:  _candle_btc_eth_ready_strategy_abc
                           ↓
EventAdapter routes to:   flow_initiator.on_data_ready()
                           ↓
FlowInitiator returns:    CONTINUE disposition
                           ↓
EventAdapter publishes:   CANDLE_STREAM_DATA_READY
  (via publication_on_continue)
                           ↓
Workers receive:          CANDLE_STREAM_DATA_READY
```

**See Also:**
- [DataProvider Design](DATA_PROVIDER_DESIGN.md#event-naming-conventions) - Provider event naming
- [EventAdapter Design](../EVENTADAPTER_DESIGN.md) - `publication_on_continue` mechanism

---

## Manifest vs Normal Plugin

### Normal Plugin (Static Inputs/Outputs)

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
- Inputs and outputs are **static** (defined in manifest)
- UI reads directly from manifest
- Never changes based on configuration

### FlowInitiator (Fixed Input, No Outputs)

```yaml
# backend/config/manifests/flow_initiator_manifest.yaml

plugin_id: "platform/flow_initiator/v1.0.0"
category: "platform_component"

capabilities:
  io:
    dynamic_outputs: false  # No output generation

inputs:
  - connector_id: "data_input"
    handler_method: "on_data_ready"

outputs: []  # 🔥 Empty - EventAdapter handles routing
```

**Characteristics:**
- Single fixed input connector (`data_input`)
- Handler method declared in manifest (`on_data_ready`)
- No outputs - EventAdapter `publication_on_continue` handles routing
- Wiring map provides event routing logic

---

## Manifest Usage Flow

### Design Time (Strategy Builder UI)

```
1. UI loads FlowInitiator manifest
   GET /api/strategy-builder/flow-initiator/manifest
   
2. UI checks: capabilities.io.dynamic_outputs === false
   → Knows FlowInitiator has no outputs to display
   
3. UI reads worker manifests with requires_capability
   → Auto-generates FlowInitiator wiring based on capability requirements
   
4. Example: SignalDetector requires "candle_stream"
   → UI generates:
     flow_initiator subscription: _candle_btc_eth_ready_{strategy_id}
     flow_initiator publication:  CANDLE_STREAM_DATA_READY
     
5. Canvas shows auto-generated wiring
   DataProvider → FlowInitiator → Workers
```

### Runtime (Bootstrap)

```
1. ConfigTranslator reads strategy_blueprint.yaml
   
2. ConfigTranslator generates WorkerBuildSpec:
   WorkerBuildSpec(
     worker_id="flow_initiator",
     worker_type="FlowInitiator",
     config={
       "dto_types": {
         "candle_stream": CandleWindow,  # Resolved Python class!
         "orderbook_snapshot": OrderBookSnapshot
       }
     }
   )
   
3. WorkerFactory instantiates FlowInitiator:
   flow_initiator = FlowInitiator("flow_initiator_strategy_abc")
   flow_initiator.configure(config, strategy_cache)
   
4. EventAdapter reads wiring map:
   subscription_config = [{
     "event_name": "_candle_btc_eth_ready_strategy_abc",
     "connector_id": "data_input",
     "handler_method": "on_data_ready",  # From manifest!
     "publication_on_continue": "candle_stream_ready"
   }]
   
5. Runtime: Provider event arrives
   → EventAdapter calls: flow_initiator.on_data_ready(platform_dto)
   → FlowInitiator returns: CONTINUE disposition
   → EventAdapter publishes: CANDLE_STREAM_DATA_READY
   → Workers receive event and pull data from StrategyCache
```

**See Also:**
- [FlowInitiator Design](FLOW_INITIATOR_DESIGN.md#architecture-overview) - Complete data flow
- [ConfigTranslator Design](../CONFIG_BUILDSPEC_TRANSLATION_DESIGN.md) - DTO type resolution

---

## Who Uses the Manifest?

| Component | Uses Manifest? | Purpose |
|-----------|---------------|---------|
| Strategy Builder UI | ✅ YES | Check handler_method, show platform component, auto-wire capabilities |
| FlowInitiatorConfigService | ✅ YES | Serve manifest to BFF API |
| WorkerFactory | ✅ YES (indirectly) | Reads handler_method from manifest during EventAdapter setup |
| EventWiringFactory | ✅ YES | Uses handler_method for subscription configuration |
| ConfigTranslator | ✅ YES | Reads metadata, generates BuildSpec with DTO types |
| FlowInitiator (worker) | ❌ NO | Receives config via WorkerBuildSpec |

---

## When Is Manifest Used?

**✅ Design Time:**
- UI queries manifest to build Strategy Builder interface
- UI reads `handler_method` from inputs
- UI checks `dynamic_outputs: false` (no output generation)
- UI auto-generates wiring based on worker capability requirements

**✅ Runtime:**
- EventAdapter reads `handler_method` from manifest
- WiringFactory uses handler_method in subscription config
- ConfigTranslator uses manifest metadata (optional)

---

## Related Documentation

- **[FlowInitiator Design](FLOW_INITIATOR_DESIGN.md)** - Complete implementation design
- **[DataProvider Design](DATA_PROVIDER_DESIGN.md)** - PlatformDataDTO producer
- **[EventAdapter Design](../EVENTADAPTER_DESIGN.md)** - `publication_on_continue` mechanism
- **[ConfigTranslator Design](../CONFIG_BUILDSPEC_TRANSLATION_DESIGN.md)** - DTO type resolution

---

**Last Updated:** 2025-11-06
