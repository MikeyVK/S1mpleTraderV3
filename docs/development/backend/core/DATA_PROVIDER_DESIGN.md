# DataProvider Design

**Status:** Design  
**Versie:** 1.0  
**Laatst Bijgewerkt:** 2025-11-06

---

## Executive Summary

DataProviders zijn **platform singleton components** die data acquisition en distributie beheren voor één of meerdere strategies binnen een ExecutionEnvironment. Ze vormen de brug tussen externe data bronnen (API's, databases, files) en strategy-specific FlowInitiators.

**Kernprincipes:**
- **Platform Singleton:** Eén provider instance per ExecutionEnvironment (niet per strategy)
- **Multi-Strategy Support:** Kan meerdere strategies bedienen via registration pattern
- **Resource Efficiency:** Shared rolling windows, single data source connection
- **Point-in-Time Guarantees:** Immutable DTOs met timestamp anchoring
- **Event-Driven:** Publiceert PlatformDataDTO events naar registered strategies

**Integration:**
```
ExecutionEnvironment → DataProviders (singletons) → FlowInitiators (per strategy) → Workers
```

---

## Problem Statement

### Multi-Strategy Execution Efficiency

**Probleem:**
10 strategies draaien op dezelfde ExecutionEnvironment (bijv. backtest):
- Alle strategies willen BTC 1h candle data
- Naive aanpak: 10× dezelfde rolling window in memory (200 candles × 10 = 2000 candles!)
- 10× dezelfde data ophalen van disk/API
- 10× dezelfde transformatie logica

**Oplossing: Platform Singleton Pattern**
- 1× RollingWindowManager voor BTC 1h (200 candles)
- 1× data source connection
- 1× transformatie logica
- Publish naar 10 strategy-specific FlowInitiators

### ExecutionEnvironment Reusability

**Probleem:**
User maakt "backtest_crypto_2023" environment met BTC/ETH data providers. Later maakt user nieuwe strategy die ook BTC/ETH wil gebruiken. Moet nieuwe environment maken?

**Oplossing:**
- ExecutionEnvironment config bevat provider definitions
- Nieuwe strategy registreert bij existing providers
- Zero configuration duplication

### Point-in-Time Data Consistency

**Probleem:**
Strategy A en Strategy B draaien parallel. Als Strategy A candle data muteert, ziet Strategy B corrupte data.

**Oplossing: Immutable DTOs**
- Pydantic `frozen=True` config
- Tuple ipv List voor candle arrays
- Runtime error bij mutatie poging

---

## Architecture Overview

### DataProvider Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│ ExecutionEnvironment (BackTest/PaperTrade/Live)             │
│                                                              │
│ Initialization:                                             │
│   1. Create DataProviders (singletons)                      │
│   2. Connect to data sources                                │
│   3. Initialize rolling windows                             │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ Strategy Registration Phase                                  │
│                                                              │
│ For each strategy in operation:                             │
│   provider.register_strategy(                               │
│       strategy_id="strategy_abc",                           │
│       symbols=["BTC", "ETH"],                               │
│       timeframes=["1h", "4h"]                               │
│   )                                                          │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ Runtime: Data Acquisition & Distribution                    │
│                                                              │
│ New candle arrives:                                          │
│   1. Update rolling window (single instance)                │
│   2. Create immutable CandleWindow DTO                      │
│   3. Wrap in PlatformDataDTO                                │
│   4. Publish to ALL registered strategies                   │
└─────────────────────────────────────────────────────────────┘
```

### Provider-FlowInitiator Communication

```
┌──────────────────────────────────────────────────────────────┐
│ CandleDataProvider (Platform Singleton)                      │
│                                                               │
│ _rolling_windows = {                                         │
│   ("BTC", "1h"): RollingWindowManager(200),                 │
│   ("ETH", "4h"): RollingWindowManager(200)                  │
│ }                                                             │
│                                                               │
│ _strategies_by_symbol_tf = {                                 │
│   ("BTC", "1h"): {"strategy_a", "strategy_c"},              │
│   ("ETH", "4h"): {"strategy_b"}                             │
│ }                                                             │
└───────────────────────────┬───────────────────────────────────┘
                            ↓ (on new BTC 1h candle)
                    ┌───────────────────┐
                    │ Update ONE window │
                    └───────────────────┘
                            ↓
        ┌───────────────────┴───────────────────┐
        ↓                                       ↓
┌──────────────────────┐            ┌──────────────────────┐
│ Publish to           │            │ Publish to           │
│ FlowInitiator        │            │ FlowInitiator        │
│ (Strategy A)         │            │ (Strategy C)         │
│                      │            │                      │
│ Event:               │            │ Event:               │
│ _candle_ready_a      │            │ _candle_ready_c      │
│                      │            │                      │
│ Payload:             │            │ Payload:             │
│ PlatformDataDTO(     │            │ PlatformDataDTO(     │
│   payload=window     │            │   payload=window     │
│ )                    │            │ )                    │
│ ← SAME window ref!   │            │ ← SAME window ref!   │
└──────────────────────┘            └──────────────────────┘
```

---

## Core Components

### 1. IDataProvider Protocol

```python
# backend/core/interfaces/data_provider.py

from __future__ import annotations
from typing import Protocol, List
from datetime import datetime


class IDataProvider(Protocol):
    """
    Protocol for platform data providers.
    
    DataProviders are platform singletons that acquire data from external
    sources and distribute to multiple strategies via event publication.
    """
    
    async def register_strategy(
        self,
        strategy_id: str,
        symbols: List[str],
        timeframes: List[str] | None = None
    ) -> None:
        """
        Register strategy for data delivery.
        
        Args:
            strategy_id: Strategy to receive data
            symbols: Trading symbols required
            timeframes: Timeframes required (provider-specific)
        """
        ...
    
    async def unregister_strategy(self, strategy_id: str) -> None:
        """
        Unregister strategy (called during strategy shutdown).
        
        Args:
            strategy_id: Strategy to stop delivering data to
        """
        ...
    
    async def start(self) -> None:
        """
        Start provider (connect to data source, begin streaming).
        Called during ExecutionEnvironment initialization.
        """
        ...
    
    async def stop(self) -> None:
        """
        Stop provider (disconnect, cleanup resources).
        Called during ExecutionEnvironment shutdown.
        """
        ...
```

---

### 2. PlatformDataDTO (SSOT)

**Complete DTO structure:**

```python
# backend/dtos/shared/platform_data.py

from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class PlatformDataDTO(BaseModel):
    """
    Minimal data envelope for DataProvider → FlowInitiator communication.

    Wraps provider DTOs with only essential metadata needed for cache
    initialization and type routing. Keeps DTO minimal following SRP.

    Design Rationale:
    - source_type: ConfigTranslator needs this for DTO type lookup
    - timestamp: FlowInitiator needs this for cache.start_new_run(timestamp)
    - payload: The actual provider data (workers extract fields from here)

    No symbol/timeframe/metadata - these are in the payload where they belong.
    """

    source_type: str = Field(
        ...,
        description="Provider type identifier for DTO type lookup in ConfigTranslator",
        min_length=1
    )

    timestamp: datetime = Field(
        ...,
        description="Point-in-time timestamp used for cache.start_new_run(timestamp)"
    )

    payload: BaseModel = Field(
        ...,
        description="Provider DTO instance (CandleWindow, OrderBookSnapshot, etc.)"
    )

    @field_validator("source_type")
    @classmethod
    def validate_source_type_not_empty(cls, value: str) -> str:
        """Validate that source_type is not empty string."""
        if not value or not value.strip():
            raise ValueError("source_type cannot be empty")
        return value

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={
            "examples": [
                {
                    "source_type": "candle_stream",
                    "timestamp": "2025-11-06T14:00:00Z",
                    "payload": {
                        "symbol": "BTC",
                        "timeframe": "1h",
                        "close": 50000.0
                    }
                }
            ]
        }
    )


# Example usage:
platform_dto = PlatformDataDTO(
    source_type="candle_stream",
    timestamp=datetime(2025, 11, 6, 14, 0, 0),
    payload=CandleWindow(...)  # Nested immutable DTO
)
```

**Field Semantics:**

| Field | Purpose | Consumer |
|-------|---------|----------|
| `source_type` | DTO type lookup key | ConfigTranslator (maps to Python class) |
| `timestamp` | RunAnchor value | FlowInitiator (cache.start_new_run()) |
| `payload` | Actual data | FlowInitiator (cache.set_result_dto()), Workers (extract fields) |

---

### 3. Immutable Provider DTOs

**All provider DTOs MUST be immutable to prevent mutation in multi-strategy scenarios.**

#### CandleWindow (Immutable)

```python
# backend/dtos/shared/candle_window.py

from __future__ import annotations
from typing import Tuple
from datetime import datetime
from pydantic import BaseModel, Field


class Candle(BaseModel):
    """Single candle data point."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    
    class Config:
        frozen = True  # Immutable


class CandleWindow(BaseModel):
    """
    Rolling window of candle data (immutable).
    
    Shared across multiple strategies via reference.
    Frozen to prevent mutation.
    """
    symbol: str
    timeframe: str
    candles: Tuple[Candle, ...]  # Tuple (immutable), not List!
    window_start: datetime
    window_end: datetime
    
    class Config:
        frozen = True  # ← CRITICAL: Prevents mutation
```

**Why Tuple instead of List?**
```python
# ❌ With List (mutable):
window.candles[0].close = 999999  # Allowed but dangerous!

# ✅ With Tuple + frozen=True:
window.candles[0].close = 999999  # pydantic.ValidationError!
```

#### OrderBookSnapshot (Immutable)

```python
# backend/dtos/shared/orderbook_snapshot.py

from __future__ import annotations
from typing import Tuple
from datetime import datetime
from pydantic import BaseModel


class OrderBookLevel(BaseModel):
    price: float
    quantity: float
    
    class Config:
        frozen = True


class OrderBookSnapshot(BaseModel):
    """Immutable orderbook snapshot."""
    symbol: str
    timestamp: datetime
    bids: Tuple[OrderBookLevel, ...]  # Immutable
    asks: Tuple[OrderBookLevel, ...]  # Immutable
    
    class Config:
        frozen = True
```

---

### 4. RollingWindowManager

```python
# backend/core/rolling_window_manager.py

from __future__ import annotations
from typing import Generic, TypeVar, Tuple
from collections import deque
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)


class RollingWindowManager(Generic[T]):
    """
    Manages fixed-size rolling window of data points.
    
    Thread-safe via immutable operations.
    Used by DataProviders to maintain historical context.
    """
    
    def __init__(self, window_size: int):
        """
        Initialize rolling window.
        
        Args:
            window_size: Maximum number of items in window (e.g., 200 candles)
        """
        self._window_size = window_size
        self._buffer: deque[T] = deque(maxlen=window_size)
    
    def add(self, item: T) -> None:
        """
        Add new item to window.
        
        Automatically removes oldest item if window is full.
        
        Args:
            item: Data point to add (must be immutable DTO)
        """
        self._buffer.append(item)
    
    def get_window(self) -> Tuple[T, ...]:
        """
        Get current window as immutable tuple.
        
        Returns:
            Tuple of all items in window (oldest to newest)
        """
        return tuple(self._buffer)
    
    def is_full(self) -> bool:
        """Check if window has reached window_size."""
        return len(self._buffer) == self._window_size
    
    def clear(self) -> None:
        """Clear all items from window."""
        self._buffer.clear()
```

**Usage in Provider:**
```python
class CandleDataProvider:
    def __init__(self):
        self._rolling_windows = {
            ("BTC", "1h"): RollingWindowManager[Candle](window_size=200),
            ("ETH", "4h"): RollingWindowManager[Candle](window_size=200)
        }
    
    async def on_new_candle(self, candle: Candle):
        key = (candle.symbol, candle.timeframe)
        window_manager = self._rolling_windows[key]
        
        # Add to window
        window_manager.add(candle)
        
        # Get immutable window
        candles_tuple = window_manager.get_window()
        
        # Create immutable CandleWindow DTO
        window = CandleWindow(
            symbol=candle.symbol,
            timeframe=candle.timeframe,
            candles=candles_tuple,  # Already a tuple
            window_start=candles_tuple[0].timestamp if candles_tuple else candle.timestamp,
            window_end=candle.timestamp
        )
```

---

### 5. CandleDataProvider Implementation

**Complete reference implementation:**

```python
# backend/core/candle_data_provider.py

from __future__ import annotations
from typing import Dict, Set, Tuple, List
from datetime import datetime
import asyncio

from backend.core.interfaces.data_provider import IDataProvider
from backend.core.interfaces.data_source import IDataSource
from backend.core.interfaces.eventbus import IEventBus
from backend.core.rolling_window_manager import RollingWindowManager
from backend.dtos.shared.candle_window import Candle, CandleWindow
from backend.dtos.shared.platform_data import PlatformDataDTO


class CandleDataProvider(IDataProvider):
    """
    Platform singleton providing candle data to multiple strategies.
    
    Responsibilities:
    - Maintain rolling windows per (symbol, timeframe)
    - Register strategies for targeted delivery
    - Publish PlatformDataDTO events to registered strategies
    - Handle strategy lifecycle (registration/unregistration)
    
    Architecture:
    - ONE instance per ExecutionEnvironment
    - Serves multiple strategies via event publication
    - Resource efficient: shared rolling windows
    """
    
    def __init__(
        self,
        provider_id: str,
        data_source: IDataSource,
        event_bus: IEventBus,
        symbols: List[str],
        timeframes: List[str],
        window_size: int = 200
    ):
        """
        Initialize candle data provider.
        
        Args:
            provider_id: Unique provider identifier (from ExecutionEnvironment config)
            data_source: Data source implementation (BackTest/Live/PaperTrade)
            event_bus: Platform EventBus for event publication
            symbols: Symbols to provide data for
            timeframes: Timeframes to provide data for
            window_size: Rolling window size (default: 200 candles)
        """
        self._provider_id = provider_id
        self._data_source = data_source
        self._event_bus = event_bus
        self._symbols = symbols
        self._timeframes = timeframes
        self._window_size = window_size
        
        # Rolling windows per (symbol, timeframe)
        self._rolling_windows: Dict[Tuple[str, str], RollingWindowManager[Candle]] = {}
        
        # Strategy registration per (symbol, timeframe)
        self._strategies_by_symbol_tf: Dict[Tuple[str, str], Set[str]] = {}
        
        # Registration lock
        self._lock = asyncio.Lock()
        
        # Initialize rolling windows
        self._initialize_windows()
    
    def _initialize_windows(self) -> None:
        """Create rolling window managers for all (symbol, timeframe) combinations."""
        for symbol in self._symbols:
            for timeframe in self._timeframes:
                key = (symbol, timeframe)
                self._rolling_windows[key] = RollingWindowManager[Candle](
                    window_size=self._window_size
                )
                self._strategies_by_symbol_tf[key] = set()
    
    async def register_strategy(
        self,
        strategy_id: str,
        symbols: List[str],
        timeframes: List[str] | None = None
    ) -> None:
        """
        Register strategy for candle data delivery.
        
        Thread-safe registration with validation.
        
        Args:
            strategy_id: Strategy to receive data
            symbols: Symbols required by strategy
            timeframes: Timeframes required (if None, all provider timeframes)
        
        Raises:
            ValueError: If requested symbols not available in provider config
        """
        async with self._lock:
            # Validate symbols
            for symbol in symbols:
                if symbol not in self._symbols:
                    raise ValueError(
                        f"Strategy '{strategy_id}' requires symbol '{symbol}' "
                        f"but provider '{self._provider_id}' only provides {self._symbols}"
                    )
            
            # Default to all timeframes if not specified
            if timeframes is None:
                timeframes = self._timeframes
            
            # Register for each (symbol, timeframe) combination
            for symbol in symbols:
                for timeframe in timeframes:
                    key = (symbol, timeframe)
                    
                    if key not in self._strategies_by_symbol_tf:
                        raise ValueError(
                            f"Provider does not support ({symbol}, {timeframe})"
                        )
                    
                    self._strategies_by_symbol_tf[key].add(strategy_id)
    
    async def unregister_strategy(self, strategy_id: str) -> None:
        """
        Unregister strategy from all symbol/timeframe combinations.
        
        Called during strategy shutdown.
        
        Args:
            strategy_id: Strategy to stop delivering data to
        """
        async with self._lock:
            for strategies in self._strategies_by_symbol_tf.values():
                strategies.discard(strategy_id)
    
    async def on_new_candle(self, candle: Candle) -> None:
        """
        Process new candle from data source.
        
        Called by ExecutionEnvironment when new candle arrives.
        
        Flow:
        1. Update rolling window (single instance)
        2. Create immutable CandleWindow DTO
        3. Wrap in PlatformDataDTO
        4. Publish to all registered strategies
        
        Args:
            candle: New candle data point
        """
        key = (candle.symbol, candle.timeframe)
        
        # 1. Update rolling window
        if key not in self._rolling_windows:
            # Symbol/timeframe not configured for this provider
            return
        
        window_manager = self._rolling_windows[key]
        window_manager.add(candle)
        
        # Get immutable window
        candles_tuple = window_manager.get_window()
        
        # 2. Create immutable CandleWindow DTO
        window = CandleWindow(
            symbol=candle.symbol,
            timeframe=candle.timeframe,
            candles=candles_tuple,
            window_start=candles_tuple[0].timestamp if candles_tuple else candle.timestamp,
            window_end=candle.timestamp
        )
        
        # 3. Get registered strategies (snapshot to avoid lock during publish)
        interested_strategies = self._strategies_by_symbol_tf.get(key, set()).copy()
        
        # 4. Publish to each registered strategy
        for strategy_id in interested_strategies:
            await self._publish_to_strategy(strategy_id, candle, window)
    
    async def _publish_to_strategy(
        self,
        strategy_id: str,
        candle: Candle,
        window: CandleWindow
    ) -> None:
        """
        Publish candle data to specific strategy.
        
        Args:
            strategy_id: Target strategy
            candle: Latest candle (for timestamp)
            window: Immutable window DTO
        """
        # Wrap in PlatformDataDTO
        platform_dto = PlatformDataDTO(
            source_type="candle_stream",
            timestamp=candle.timestamp,
            symbol=candle.symbol,
            timeframe=candle.timeframe,
            payload=window  # Immutable DTO
        )
        
        try:
            # Publish strategy-scoped event
            await self._event_bus.publish(
                event_name=f"_{self._provider_id}_ready_{strategy_id}",
                payload=platform_dto,
                scope="STRATEGY",
                strategy_id=strategy_id
            )
        except Exception as e:
            # Strategy not listening? Auto-unregister
            await self.unregister_strategy(strategy_id)
    
    async def start(self) -> None:
        """Start provider (connect to data source)."""
        # Data source connection logic here
        pass
    
    async def stop(self) -> None:
        """Stop provider (disconnect, cleanup)."""
        # Cleanup logic here
        pass
```

---

## Multi-Strategy Patterns

### Pattern 1: Symbol Overlap

**Scenario:** Strategy A and Strategy C both want BTC 1h data.

```python
# Registration
await candle_provider.register_strategy(
    strategy_id="strategy_a",
    symbols=["BTC"],
    timeframes=["1h"]
)

await candle_provider.register_strategy(
    strategy_id="strategy_c",
    symbols=["BTC"],
    timeframes=["1h"]
)

# Internal state:
# _strategies_by_symbol_tf = {
#     ("BTC", "1h"): {"strategy_a", "strategy_c"}
# }

# New candle arrives:
await candle_provider.on_new_candle(candle_btc_1h)

# Result:
# - ONE rolling window updated
# - TWO events published:
#   1. "_candle_btc_eth_ready_strategy_a" (Strategy A)
#   2. "_candle_btc_eth_ready_strategy_c" (Strategy C)
# - SAME window instance in both events (memory efficient)
```

### Pattern 2: Different Timeframes

**Scenario:** Strategy A wants BTC 1h, Strategy B wants ETH 4h.

```python
# Registration
await candle_provider.register_strategy("strategy_a", ["BTC"], ["1h"])
await candle_provider.register_strategy("strategy_b", ["ETH"], ["4h"])

# Internal state:
# _strategies_by_symbol_tf = {
#     ("BTC", "1h"): {"strategy_a"},
#     ("ETH", "4h"): {"strategy_b"}
# }

# New BTC 1h candle:
await candle_provider.on_new_candle(candle_btc_1h)
# → Only Strategy A receives event

# New ETH 4h candle:
await candle_provider.on_new_candle(candle_eth_4h)
# → Only Strategy B receives event
```

### Pattern 3: Platform-Scoped Events

**Scenario:** AggregatedLedger (platform singleton) broadcasts budget alert.

```python
# Platform component publishes
class AggregatedLedger:
    async def on_budget_exceeded(self):
        await self._event_bus.publish(
            event_name="_BUDGET_EXCEEDED",
            payload=BudgetAlertDTO(...),
            scope="PLATFORM"  # ← Broadcast to ALL strategies
        )

# ALL FlowInitiators receive event
# Each FlowInitiator processes for its own strategy:
# - Initializes StrategyCache
# - Stores BudgetAlertDTO
# - Triggers strategy-specific workers
```

---

## ExecutionEnvironment Integration

### ExecutionEnvironment Config Schema

```yaml
# execution_environments/backtest_crypto_2023.yaml

id: "backtest_crypto_2023"
type: "backtest"
description: "Historical crypto data 2023"

data_providers:
  - provider_type: "candle_stream"
    provider_id: "candle_btc_eth"  # Unique ID for event naming
    connector: "parquet_reader"
    config:
      data_dir: "./data/historical/2023"
      symbols: ["BTC", "ETH"]
      timeframes: ["1h", "4h"]
      window_size: 200
    dto_type: "CandleWindow"  # For ConfigTranslator type resolution
  
  - provider_type: "orderbook_snapshot"
    provider_id: "orderbook_btc"
    connector: "parquet_reader"
    config:
      data_dir: "./data/orderbooks/2023"
      symbols: ["BTC"]
      depth: 10
    dto_type: "OrderBookSnapshot"

replay_config:
  start_date: "2023-01-01"
  end_date: "2023-12-31"
  speed: "fast"
```

**Field Semantics:**

| Field | Purpose | Used By |
|-------|---------|---------|
| `provider_type` | Capability identifier | Worker manifest matching |
| `provider_id` | Event naming (`_{provider_id}_ready`) | Event generation |
| `connector` | Data source implementation | ExecutionEnvironment factory |
| `dto_type` | DTO class name | ConfigTranslator type resolution |
| `config` | Provider-specific settings | Provider initialization |

### ExecutionEnvironment Implementation

```python
# backend/execution_environments/backtest_environment.py

class BackTestEnvironment:
    """
    BackTest execution environment with DataProvider management.
    """
    
    def __init__(self, config: dict):
        self._config = config
        self._providers: Dict[str, IDataProvider] = {}
        self._event_bus: IEventBus = EventBus()
    
    def initialize_providers(self) -> None:
        """Create and initialize all data providers."""
        for provider_config in self._config["data_providers"]:
            provider = self._create_provider(provider_config)
            self._providers[provider_config["provider_id"]] = provider
    
    def _create_provider(self, config: dict) -> IDataProvider:
        """Factory method for provider creation."""
        provider_type = config["provider_type"]
        
        if provider_type == "candle_stream":
            data_source = self._create_data_source(config)
            return CandleDataProvider(
                provider_id=config["provider_id"],
                data_source=data_source,
                event_bus=self._event_bus,
                symbols=config["config"]["symbols"],
                timeframes=config["config"]["timeframes"],
                window_size=config["config"].get("window_size", 200)
            )
        # ... other provider types
    
    def get_provider(self, provider_id: str) -> IDataProvider:
        """Get provider by ID."""
        return self._providers.get(provider_id)
    
    async def run(self) -> None:
        """
        Execute backtest replay.
        
        Sequential execution: advance time → emit candles → wait for completion.
        """
        replay_engine = self._create_replay_engine()
        
        # Start all providers
        for provider in self._providers.values():
            await provider.start()
        
        # Replay loop
        async for time_point in replay_engine.advance():
            # Get candles for this timestamp
            candles = await self._data_source.get_candles_at(time_point)
            
            # Emit to providers
            for candle in candles:
                provider = self._get_provider_for_candle(candle)
                await provider.on_new_candle(candle)
            
            # Wait for all strategies to complete processing
            await self._event_bus.flush()
```

### Strategy Registration During Wiring

```python
# backend/services/operation_service.py

class OperationService:
    """
    Orchestrates strategy lifecycle including provider registration.
    """
    
    async def start_strategy(self, strategy_link: StrategyLink):
        # 1. Load ExecutionEnvironment
        exec_env = self._load_execution_environment(strategy_link.exec_env_id)
        
        # 2. Collect strategy requirements from workers
        requirements = self._collect_worker_requirements(strategy_link.blueprint)
        # requirements = [
        #     {"capability": "candle_stream", "symbols": ["BTC"], "timeframes": ["1h"]},
        #     {"capability": "orderbook_snapshot", "symbols": ["BTC"]}
        # ]
        
        # 3. Validate: ExecutionEnvironment provides required capabilities?
        self._validate_environment_compatibility(requirements, exec_env)
        
        # 4. Register strategy with providers
        for req in requirements:
            provider = exec_env.get_provider_by_type(req["capability"])
            
            await provider.register_strategy(
                strategy_id=strategy_link.id,
                symbols=req["symbols"],
                timeframes=req.get("timeframes")
            )
        
        # 5. Continue with worker creation and wiring...
```

---

## Event Naming Convention

**Pattern:** `_{provider_id}_ready_{strategy_id}`

**Examples:**
```
_candle_btc_eth_ready_strategy_abc123
_orderbook_btc_ready_strategy_xyz789
_bloomberg_news_ready_strategy_def456
```

**Rationale:**
- `_` prefix: Internal platform event (not user-defined)
- `{provider_id}`: Identifies data source
- `_ready`: Semantic meaning (data is ready)
- `_{strategy_id}`: Target strategy (strategy-scoped delivery)

**EventBus scoping:**
```python
await event_bus.publish(
    event_name="_candle_btc_eth_ready_strategy_abc",
    payload=platform_dto,
    scope="STRATEGY",  # Only this strategy receives
    strategy_id="strategy_abc"
)
```

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/core/test_candle_data_provider.py

class TestCandleDataProvider:
    """Unit tests for CandleDataProvider."""
    
    def test_register_strategy_adds_to_subscription_map(self):
        """Test strategy registration updates internal mapping."""
        provider = CandleDataProvider(
            provider_id="test_provider",
            data_source=Mock(),
            event_bus=Mock(),
            symbols=["BTC"],
            timeframes=["1h"],
            window_size=200
        )
        
        await provider.register_strategy(
            strategy_id="strategy_a",
            symbols=["BTC"],
            timeframes=["1h"]
        )
        
        # Verify internal state
        assert ("BTC", "1h") in provider._strategies_by_symbol_tf
        assert "strategy_a" in provider._strategies_by_symbol_tf[("BTC", "1h")]
    
    def test_on_new_candle_publishes_to_registered_strategies(self):
        """Test candle emission to multiple strategies."""
        event_bus = Mock(spec=IEventBus)
        provider = CandleDataProvider(
            provider_id="test_provider",
            data_source=Mock(),
            event_bus=event_bus,
            symbols=["BTC"],
            timeframes=["1h"],
            window_size=200
        )
        
        # Register two strategies
        await provider.register_strategy("strategy_a", ["BTC"], ["1h"])
        await provider.register_strategy("strategy_b", ["BTC"], ["1h"])
        
        # Emit candle
        candle = Candle(
            timestamp=datetime.now(),
            open=50000,
            high=51000,
            low=49000,
            close=50500,
            volume=100
        )
        await provider.on_new_candle(candle)
        
        # Verify two publish calls
        assert event_bus.publish.call_count == 2
        
        # Verify event names
        calls = event_bus.publish.call_args_list
        event_names = [call[1]["event_name"] for call in calls]
        assert "_test_provider_ready_strategy_a" in event_names
        assert "_test_provider_ready_strategy_b" in event_names
    
    def test_immutable_window_shared_across_strategies(self):
        """Test same window instance published to multiple strategies."""
        event_bus = Mock(spec=IEventBus)
        provider = CandleDataProvider(...)
        
        await provider.register_strategy("strategy_a", ["BTC"], ["1h"])
        await provider.register_strategy("strategy_b", ["BTC"], ["1h"])
        
        await provider.on_new_candle(candle)
        
        # Extract payloads from both publish calls
        calls = event_bus.publish.call_args_list
        payload_a = calls[0][1]["payload"].payload
        payload_b = calls[1][1]["payload"].payload
        
        # Verify same object reference (memory efficiency)
        assert payload_a is payload_b
    
    def test_immutable_dto_prevents_mutation(self):
        """Test frozen DTOs raise error on mutation attempt."""
        window = CandleWindow(
            symbol="BTC",
            timeframe="1h",
            candles=tuple([candle1, candle2]),
            window_start=datetime.now(),
            window_end=datetime.now()
        )
        
        # Attempt mutation
        with pytest.raises(ValidationError):
            window.candles[0].close = 999999  # Should raise!
```

### Integration Tests

```python
# tests/integration/test_provider_flow_initiator.py

class TestProviderFlowInitiatorIntegration:
    """Integration tests for complete data flow."""
    
    async def test_complete_flow_provider_to_workers(self):
        """Test end-to-end: Provider → FlowInitiator → Workers."""
        # Setup
        event_bus = EventBus()
        exec_env = BackTestEnvironment(config)
        exec_env.initialize_providers()
        
        # Create strategy components
        strategy_cache = StrategyCache()
        flow_initiator = FlowInitiator("flow_init_1")
        worker = MomentumDetector("detector_1")
        
        # Register strategy with provider
        provider = exec_env.get_provider("candle_btc_eth")
        await provider.register_strategy(
            strategy_id="strategy_test",
            symbols=["BTC"],
            timeframes=["1h"]
        )
        
        # Wire FlowInitiator
        flow_adapter = EventAdapter(
            worker=flow_initiator,
            event_bus=event_bus,
            strategy_id="strategy_test",
            subscriptions=[{
                "event_name": "_candle_btc_eth_ready_strategy_test",
                "connector_id": "data_input",
                "publication_on_continue": "candle_stream_ready"
            }]
        )
        
        # Wire Worker
        worker_adapter = EventAdapter(
            worker=worker,
            event_bus=event_bus,
            subscriptions=[{
                "event_name": "CANDLE_STREAM_DATA_READY",
                "connector_id": "candle_trigger"
            }]
        )
        
        # Emit candle
        candle = Candle(timestamp=datetime.now(), open=50000, ...)
        await provider.on_new_candle(candle)
        
        # Verify flow
        assert strategy_cache.get_run_anchor() is not None  # Cache initialized
        assert strategy_cache.get_required_dtos()[CandleWindow] is not None  # Data stored
        # Worker received event and processed
```

---

## Related Documentation

- **[FlowInitiator Design](FLOW_INITIATOR_DESIGN.md)** - Consumer of PlatformDataDTO, cache initialization
- **[EventAdapter Design](../EVENTADAPTER_DESIGN.md)** - Event routing infrastructure
- **[ExecutionEnvironment Design](../execution_environments/README.md)** - Environment lifecycle and configuration
- **[Point-in-Time Model](../../../architecture/POINT_IN_TIME_MODEL.md)** - Immutability and temporal consistency

---

**Last Updated:** 2025-11-06
