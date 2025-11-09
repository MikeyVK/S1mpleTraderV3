# FlowInitiator Design

**Status:** ✅ Implemented (Phase 1.3)  
**Versie:** 2.0  
**Laatst Bijgewerkt:** 2025-11-09  
**Implementation:** `backend/core/flow_initiator.py`  
**Tests:** 14/14 passing (100% coverage)  
**Quality:** Pylint 10/10

---

## Executive Summary

FlowInitiator is een **per-strategy platform component** die verantwoordelijk is voor het initiëren van strategy pipeline runs door data van DataProviders op te slaan in StrategyCache en workers te triggeren.

**Kernprincipes:**
- **Per-Strategy Instance:** Elke strategy heeft eigen FlowInitiator (niet singleton)
- **EventAdapter-Compliant:** Volgt standard IWorker pattern met handler methods
- **Data Consumer:** Ontvangt PlatformDataDTO van DataProviders
- **Cache Manager:** Initialiseert StrategyCache (start_new_run) en slaat data op (set_result_dto)
- **Type-Safe:** DTO type resolution via ConfigTranslator registry (geen runtime type checking)

**Integration:**
```
DataProvider → FlowInitiator (per strategy) → StrategyCache → Workers
```

---

## Problem Statement

### Race Condition Prevention

**Probleem:**
Workers subscriben direct op data events zonder garantie dat StrategyCache geïnitialiseerd is:

```python
# ❌ ZONDER FlowInitiator:
class SignalDetector:
    def on_candle_close(self, candle_data):
        anchor = self._cache.get_run_anchor()  # 💥 NoActiveRunError!
        # Niemand heeft cache.start_new_run() aangeroepen
```

**Oplossing: FlowInitiator initialiseert cache VOOR workers worden getriggerd**

```python
# ✅ MET FlowInitiator:
# 1. DataProvider publiceert event
# 2. FlowInitiator.on_data_ready() → cache.start_new_run() ✅
# 3. FlowInitiator returns CONTINUE
# 4. EventAdapter publiceert naar workers
# 5. Worker.on_candle_close() → cache.get_run_anchor() ✅ Exists!
```

### Type-Safe Data Storage

**Probleem:**
StrategyCache werkt met `Dict[Type[BaseModel], BaseModel]`. FlowInitiator moet correct DTO type opslaan zonder hardcoded type checks.

**Oplossing: ConfigTranslator injecteert resolved DTO types**

```python
# ConfigTranslator genereert:
buildspec.config = {
    "dto_types": {
        "candle_stream": CandleWindow,  # ← Python class, niet string!
        "orderbook_snapshot": OrderBookSnapshot
    }
}

# FlowInitiator ontvangt al-resolved types:
dto_type = self._dto_types["candle_stream"]  # CandleWindow class
```

---

## Architecture Overview

### FlowInitiator in Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│ DataProvider (Platform Singleton)                           │
│   - CandleDataProvider                                      │
│   - Publiceert: PlatformDataDTO                            │
│   - Event: "_candle_btc_eth_ready_{strategy_id}"           │
└────────────────────┬────────────────────────────────────────┘
                     ↓
        PlatformDataDTO(source_type="candle_stream", ...)
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ EventBus                                                     │
│   - Strategy-scoped event delivery                          │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ FlowInitiator EventAdapter (Per-Strategy)                   │
│   - Subscription: "_candle_btc_eth_ready_strategy_abc"     │
│   - Calls: flow_initiator.on_data_ready(platform_dto)      │
│   - publication_on_continue: "candle_stream_ready"         │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ FlowInitiator.on_data_ready()                               │
│   1. cache.start_new_run(timestamp) ✅ Initialize           │
│   2. cache.set_result_dto(payload) ✅ Store by TYPE         │
│   3. return CONTINUE disposition                            │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ EventAdapter handles CONTINUE                                │
│   - Publiceert: "CANDLE_STREAM_DATA_READY"                 │
│   - (via publication_on_continue mapping)                   │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ Workers (SignalDetector, etc.)                               │
│   - Subscription: "CANDLE_STREAM_DATA_READY"                │
│   - Halen data UIT StrategyCache:                           │
│     cache.get_required_dtos()[CandleWindow]                 │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Single handler method** | `on_data_ready()` handles ALL data types (candles, news, orderbook) |
| **CONTINUE disposition** | EventAdapter handles routing, niet FlowInitiator |
| **DTO types injected** | ConfigTranslator resolves types, FlowInitiator blijft generic |
| **No output_map** | EventAdapter `publication_on_continue` doet event routing |
| **Per-strategy instance** | Elke strategy heeft isolated cache lifecycle |

---

## Component Design

### FlowInitiator Implementation

```python
# backend/core/flow_initiator.py

from __future__ import annotations
from typing import TYPE_CHECKING, Type, Dict, Any
from pydantic import BaseModel

from backend.core.interfaces.worker import IWorker
from backend.core.interfaces.strategy_cache import IStrategyCache
from backend.dtos.shared.disposition_envelope import DispositionEnvelope, Disposition

if TYPE_CHECKING:
    from backend.dtos.shared.platform_data import PlatformDataDTO


class FlowInitiator(IWorker):
    """
    Per-strategy data ingestion and cache initialization component.
    
    Responsibilities:
    1. Initialize StrategyCache for new run (start_new_run)
    2. Store provider DTOs in cache by TYPE (set_result_dto)
    3. Return CONTINUE disposition to trigger workers
    
    Architecture Principles:
    - EventAdapter-compliant: Standard IWorker pattern
    - Type-safe: DTO types injected via ConfigTranslator
    - Bus-agnostic: No event name knowledge, uses DispositionEnvelope
    - Generic: Single handler for all data types
    """
    
    def __init__(self, worker_id: str):
        self._worker_id = worker_id
        self._cache: IStrategyCache | None = None
        self._dto_types: Dict[str, Type[BaseModel]] = {}
    
    def configure(self, config: dict[str, Any], cache: IStrategyCache) -> None:
        """
        Configure with BuildSpec config from ConfigTranslator.
        
        Config structure (generated by ConfigTranslator):
        {
            "dto_types": {
                "candle_stream": <CandleWindow class>,  # Already resolved!
                "orderbook_snapshot": <OrderBookSnapshot class>,
                "sentiment": <SentimentDTO class>
            }
        }
        """
        self._cache = cache
        self._dto_types = config.get("dto_types", {})
    
    def on_data_ready(self, data: PlatformDataDTO) -> DispositionEnvelope:
        """
        Handle data ready event from DataProvider.
        
        Flow:
        1. Initialize StrategyCache with RunAnchor
        2. Lookup DTO type from source_type
        3. Store payload in cache by TYPE
        4. Return CONTINUE disposition (EventAdapter publishes next event)
        """
        # 1. Initialize StrategyCache
        self._cache.start_new_run({}, data.timestamp)
        
        # 2. Lookup DTO type for validation
        dto_type = self._dto_types.get(data.source_type)
        
        if not dto_type:
            raise ValueError(
                f"No DTO type mapping for source_type: {data.source_type}. "
                f"Available: {list(self._dto_types.keys())}. "
                f"Check ExecutionEnvironment provider configuration."
            )
        
        # 3. Store in StrategyCache by TYPE
        self._cache.set_result_dto(data.payload)
        
        # 4. Return CONTINUE disposition
        return DispositionEnvelope(disposition=Disposition.CONTINUE)
    
    def get_worker_id(self) -> str:
        return self._worker_id
    
    def cleanup(self) -> None:
        pass
```

---

## ConfigTranslator Integration

### DTO Type Registry (SSOT)

```python
# backend/assembly/config_translator.py

class ConfigTranslator:
    """THE THINKER - All decision logic including DTO type resolution."""
    
    def __init__(self):
        self._dto_type_registry = self._build_dto_type_registry()
    
    def _build_dto_type_registry(self) -> Dict[str, Type[BaseModel]]:
        """
        Build centralized DTO type registry.
        
        This is the ONLY place where DTO types are imported and registered.
        Add new DTOs here when extending system.
        """
        from backend.dtos.shared import (
            CandleWindow,
            OrderBookSnapshot,
            SentimentDTO,
            NewsEventDTO,
        )
        
        return {
            "CandleWindow": CandleWindow,
            "OrderBookSnapshot": OrderBookSnapshot,
            "SentimentDTO": SentimentDTO,
            "NewsEventDTO": NewsEventDTO,
            # New DTO? Add one line here, done!
        }
    
    def _resolve_dto_type(self, type_name: str) -> Type[BaseModel]:
        """Resolve DTO type from name using centralized registry."""
        if type_name not in self._dto_type_registry:
            raise ValueError(
                f"Unknown DTO type: {type_name}. "
                f"Available types: {list(self._dto_type_registry.keys())}. "
                f"Add new types to ConfigTranslator._build_dto_type_registry()"
            )
        
        return self._dto_type_registry[type_name]
```

### BuildSpec Generation

```python
class ConfigTranslator:
    def translate_flow_initiator(
        self,
        strategy_config: dict,
        execution_env: dict,
        strategy_cache: IStrategyCache
    ) -> WorkerBuildSpec:
        """
        Generate FlowInitiator BuildSpec with RESOLVED DTO types.
        
        Flow:
        1. Collect capability requirements from strategy workers
        2. Match capabilities to ExecutionEnvironment providers
        3. Resolve DTO type names to Python classes
        4. Generate BuildSpec with resolved types
        """
        # 1. Collect capability requirements
        capability_reqs = self._collect_worker_capabilities(strategy_config["workers"])
        
        # 2. Build DTO type mappings (RESOLVED classes, not strings!)
        dto_types = {}
        
        for req in capability_reqs:
            provider = self._find_provider(execution_env, req["capability"])
            dto_type_name = provider.get("dto_type")
            
            if dto_type_name:
                # ✅ RESOLVE TYPE HERE (not in FlowInitiator!)
                dto_type = self._resolve_dto_type(dto_type_name)
                dto_types[provider["provider_type"]] = dto_type
        
        # 3. Return BuildSpec with RESOLVED types
        return WorkerBuildSpec(
            worker_id="flow_initiator",
            worker_type="FlowInitiator",
            config={"dto_types": dto_types}  # ← Classes, not strings!
        )
```

---

## EventAdapter Wiring

### Subscription Pattern with publication_on_continue

```yaml
# strategy_wiring_map.yaml

flow_initiator:
  subscriptions:
    - event_name: "_candle_btc_eth_ready_{strategy_id}"
      connector_id: "data_input"
      publication_on_continue: "candle_stream_ready"  # ← Routes CONTINUE
    
    - event_name: "_bloomberg_news_ready_{strategy_id}"
      connector_id: "data_input"  # SAME handler!
      publication_on_continue: "news_feed_ready"
  
  publications:
    - connector_id: "candle_stream_ready"
      event_name: "CANDLE_STREAM_DATA_READY"
    
    - connector_id: "news_feed_ready"
      event_name: "NEWS_FEED_DATA_READY"
```

**Waarom `publication_on_continue`?**
- ✅ FlowInitiator returns generic CONTINUE (geen connector_id)
- ✅ EventAdapter weet welk event te publiceren (per subscription)
- ✅ Dezelfde handler (`on_data_ready`) voor alle data types
- ✅ Routing configuratie in wiring, niet in FlowInitiator code

---

## StrategyCache Integration

### Cache Initialization

```python
# FlowInitiator calls start_new_run()
self._cache.start_new_run({}, data.timestamp)

# StrategyCache internal state:
# _current_cache = {}  # Fresh empty dict
# _current_anchor = RunAnchor(timestamp=data.timestamp)
```

**Effect:**
- ✅ RunAnchor created → Workers kunnen `cache.get_run_anchor()` aanroepen
- ✅ Empty cache → Clean slate voor nieuwe run
- ✅ Point-in-time freeze → Timestamp locked

### Data Storage by TYPE

```python
# FlowInitiator stores payload
self._cache.set_result_dto(data.payload)  # data.payload = CandleWindow(...)

# StrategyCache implementation:
def set_result_dto(self, dto: BaseModel) -> None:
    dto_type = type(dto)  # CandleWindow class
    self._current_cache[dto_type] = dto

# Result: _current_cache = {CandleWindow: CandleWindow(...)}
```

### Worker Retrieval

```python
class SignalDetector:
    def on_candle_close(self) -> DispositionEnvelope:
        # ✅ Get data by TYPE (no key strings!)
        candle_window = self._cache.get_required_dtos()[CandleWindow]
        
        # Business logic
        latest_candle = candle_window.candles[-1]
        if latest_candle.close > latest_candle.open:
            signal = SignalDTO(...)
            self._cache.set_result_dto(signal)
        
        return DispositionEnvelope(disposition=Disposition.CONTINUE)
```

---

## Design Principles

### 1. EventAdapter Compliance

FlowInitiator volgt exact hetzelfde patroon als andere workers:

```python
# ✅ Standard IWorker pattern
class FlowInitiator(IWorker):
    def configure(self, config: dict, cache: IStrategyCache) -> None: ...
    def on_data_ready(self, payload: BaseModel) -> DispositionEnvelope: ...
    def get_worker_id(self) -> str: ...
    def cleanup(self) -> None: ...
```

### 2. Single Responsibility

FlowInitiator heeft ALLEEN deze verantwoordelijkheden:
- ✅ Initialize StrategyCache (start_new_run)
- ✅ Store data in cache (set_result_dto)
- ✅ Return CONTINUE disposition

**NIET verantwoordelijk voor:**
- ❌ Event routing (dat doet EventAdapter)
- ❌ DTO transformatie (DTOs komen al klaar van providers)
- ❌ Worker triggering (dat doet EventAdapter)

### 3. Type Safety via Injection

```python
# ✅ ConfigTranslator resolves types
config = {"dto_types": {"candle_stream": CandleWindow}}  # Class!

# ✅ FlowInitiator receives resolved types
self._dto_types = config["dto_types"]

# ✅ No runtime isinstance() checks needed
dto_type = self._dto_types[data.source_type]  # Direct lookup
```

### 4. Extensibility

**Nieuwe DTO type toevoegen:**

```python
# 1. Create DTO
class TwitterSentimentDTO(BaseModel):
    class Config:
        frozen = True

# 2. Register in ConfigTranslator (ONLY place!)
def _build_dto_type_registry(self):
    return {
        "CandleWindow": CandleWindow,
        "TwitterSentimentDTO": TwitterSentimentDTO,  # ← Add here
    }

# 3. Update ExecutionEnvironment config
data_providers:
  - provider_type: "twitter_sentiment"
    dto_type: "TwitterSentimentDTO"

# FlowInitiator code? UNCHANGED! ✅
```

---

## Related Documentation

- **[DataProvider Design](DATA_PROVIDER_DESIGN.md)** - Producer of PlatformDataDTO
- **[FlowInitiator Manifest](FLOW_INITIATOR_MANIFEST.md)** - Manifest structure  
- **[EventAdapter Design](../EVENTADAPTER_DESIGN.md)** - publication_on_continue mechanism
- **[StrategyCache Design](../../../reference/platform/strategy_cache.md)** - Cache lifecycle

---

**Last Updated:** 2025-11-06