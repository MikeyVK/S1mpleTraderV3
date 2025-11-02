# StrategyCache Reference Implementation

## Overview

**File:** `backend/core/strategy_cache.py`

The `StrategyCache` is the **concrete singleton implementation** of the `IStrategyCache` protocol. It manages Point-in-Time DTO storage for strategy runs, ensuring data isolation and consistency.

## Architecture Context

**Layer:** Backend (Core Services)

**Design Philosophy:** Point-in-Time Data Model
- No growing DataFrames
- DTOs only (immutable data contracts)
- Run-scoped isolation via TickCache
- Single source of truth per strategy run

**Related Documentation:**
- Protocol: [IStrategyCache](../../architecture/POINT_IN_TIME_MODEL.md#istrategycache-protocol)
- Architecture: [Point-in-Time Model](../../architecture/POINT_IN_TIME_MODEL.md)
- Tests: `tests/unit/core/test_strategy_cache.py` (20 tests)

## Implementation Overview

### Singleton Pattern

StrategyCache is a **module-level singleton** to ensure single instance across application.

```python
# backend/core/strategy_cache.py
from backend.core.interfaces.strategy_cache import (
    IStrategyCache,
    RunAnchor,
    StrategyCacheType
)

class StrategyCache(IStrategyCache):
    """Concrete singleton implementation of IStrategyCache protocol."""
    
    def __init__(self):
        """Initialize empty strategy cache state."""
        self._current_cache: StrategyCacheType | None = None
        self._current_anchor: RunAnchor | None = None

# Module-level singleton instance
strategy_cache: IStrategyCache = StrategyCache()
```

**Why singleton:**
- Single source of truth for current run
- Prevents accidental multiple caches
- Simple import: `from backend.core.strategy_cache import strategy_cache`

### State Management

StrategyCache maintains two pieces of state:

1. **`_current_cache`** - The active TickCache dictionary
2. **`_current_anchor`** - The frozen RunAnchor (timestamp validation)

**State transitions:**

```
Initial → start_run() → Active → clear() → Initial
                    ↓
                get_run_anchor()
                set_dto()
                get_dtos()
                has_dto()
```

## API Reference

### start_run()

**Signature:**
```python
def start_run(
    self,
    tick_cache: StrategyCacheType,
    timestamp: datetime
) -> None
```

**Purpose:** Configure cache for new strategy run

**Parameters:**
- `tick_cache` - The TickCache dictionary from TickCacheManager
- `timestamp` - Run timestamp (converted to UTC if naive)

**Raises:**
- `ValueError` - If cache already configured (call `clear()` first)
- `CacheNotConfiguredError` - If timestamp validation fails

**Example:**
```python
from backend.core.strategy_cache import strategy_cache

# Start new run
tick_cache = {}
timestamp = datetime.now(timezone.utc)
strategy_cache.start_run(tick_cache, timestamp)
```

**Implementation:**
```python
def start_run(
    self,
    tick_cache: StrategyCacheType,
    timestamp: datetime
) -> None:
    """Configure cache for new strategy run."""
    if self._current_cache is not None:
        raise ValueError(
            "Cache already configured. Call clear() first."
        )
    
    # Ensure UTC
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    else:
        timestamp = timestamp.astimezone(timezone.utc)
    
    # Configure state
    self._current_cache = tick_cache
    self._current_anchor = RunAnchor(timestamp=timestamp)
```

### get_run_anchor()

**Signature:**
```python
def get_run_anchor(self) -> RunAnchor
```

**Purpose:** Get current run's frozen timestamp

**Returns:** `RunAnchor` - Frozen Pydantic model with timestamp

**Raises:**
- `CacheNotConfiguredError` - If `start_run()` not called yet

**Example:**
```python
anchor = strategy_cache.get_run_anchor()
print(f"Run timestamp: {anchor.timestamp}")
```

**Implementation:**
```python
def get_run_anchor(self) -> RunAnchor:
    """Get current run's frozen timestamp."""
    if self._current_anchor is None:
        raise CacheNotConfiguredError(
            "Cannot get RunAnchor - cache not configured. "
            "Call start_run() first."
        )
    return self._current_anchor
```

### set_dto()

**Signature:**
```python
def set_dto(self, key: str, dto: BaseModel) -> None
```

**Purpose:** Store DTO in current run's cache

**Parameters:**
- `key` - DTO key (e.g., "signals", "indicator_data")
- `dto` - Pydantic BaseModel DTO to store

**Raises:**
- `CacheNotConfiguredError` - If cache not configured
- `TypeError` - If dto is not a Pydantic BaseModel

**Example:**
```python
from backend.dtos.strategy.signal import Signal

signal = Signal(...)
strategy_cache.set_dto("signals", signal)
```

**Implementation:**
```python
def set_dto(self, key: str, dto: BaseModel) -> None:
    """Store DTO in current run's cache."""
    if self._current_cache is None:
        raise CacheNotConfiguredError(
            "Cannot set DTO - cache not configured. "
            "Call start_run() first."
        )
    
    if not isinstance(dto, BaseModel):
        raise TypeError(
            f"dto must be Pydantic BaseModel, got {type(dto).__name__}"
        )
    
    # Store in TickCache
    if key not in self._current_cache:
        self._current_cache[key] = []
    self._current_cache[key].append(dto)
```

### get_dtos()

**Signature:**
```python
def get_dtos(self, key: str, dto_type: type[T]) -> list[T]
```

**Purpose:** Retrieve all DTOs of specific type from current run

**Parameters:**
- `key` - DTO key to retrieve
- `dto_type` - Expected DTO type (for type safety)

**Returns:** `list[T]` - List of DTOs of specified type

**Raises:**
- `CacheNotConfiguredError` - If cache not configured
- `InvalidDTOTypeError` - If stored DTOs don't match expected type

**Example:**
```python
signals = strategy_cache.get_dtos(
    "signals",
    Signal
)

for signal in signals:
    print(signal.signal_type)
```

**Implementation:**
```python
def get_dtos(self, key: str, dto_type: type[T]) -> list[T]:
    """Retrieve all DTOs of specific type from current run."""
    if self._current_cache is None:
        raise CacheNotConfiguredError(
            "Cannot get DTOs - cache not configured. "
            "Call start_run() first."
        )
    
    dtos = self._current_cache.get(key, [])
    
    # Type validation
    for dto in dtos:
        if not isinstance(dto, dto_type):
            raise InvalidDTOTypeError(
                f"Expected {dto_type.__name__}, "
                f"got {type(dto).__name__} for key '{key}'"
            )
    
    return dtos  # type: ignore[return-value]
```

### has_dto()

**Signature:**
```python
def has_dto(self, key: str) -> bool
```

**Purpose:** Check if key exists in current run's cache

**Parameters:**
- `key` - DTO key to check

**Returns:** `bool` - True if key exists with non-empty list

**Raises:**
- `CacheNotConfiguredError` - If cache not configured

**Example:**
```python
if strategy_cache.has_dto("signals"):
    signals = strategy_cache.get_dtos("signals", Signal)
```

**Implementation:**
```python
def has_dto(self, key: str) -> bool:
    """Check if key exists in current run's cache."""
    if self._current_cache is None:
        raise CacheNotConfiguredError(
            "Cannot check DTO - cache not configured. "
            "Call start_run() first."
        )
    
    return key in self._current_cache and len(self._current_cache[key]) > 0
```

### clear()

**Signature:**
```python
def clear(self) -> None
```

**Purpose:** Reset cache to initial state (end of run)

**Example:**
```python
# End of strategy run
strategy_cache.clear()
```

**Implementation:**
```python
def clear(self) -> None:
    """Reset cache to initial state."""
    self._current_cache = None
    self._current_anchor = None
```

## Usage Patterns

### Worker Access Pattern

Workers should **inject `IStrategyCache`** via dependency injection (future), or import module singleton for now.

```python
# backend/workers/opportunity_worker.py
from backend.core.strategy_cache import strategy_cache
from backend.dtos.strategy.signal import Signal

class OpportunityWorker:
    def process(self, tick: RawTick) -> DispositionEnvelope:
        # Get run anchor
        anchor = strategy_cache.get_run_anchor()
        
        # Detect signal
        signal = Signal(...)
        
        # Store in cache
        strategy_cache.set_dto("signals", signal)
        
        return DispositionEnvelope(
            disposition=Disposition.PUBLISH,
            event_name="OPPORTUNITY_DETECTED",
            payload=signal
        )
```

### Flow Orchestration Pattern

TickCacheManager orchestrates complete flow lifecycle:

```python
# backend/core/tick_cache_manager.py
class TickCacheManager:
    def on_raw_tick(self, tick: RawTick):
        # 1. Create new TickCache
        tick_cache = {}
        
        # 2. Configure StrategyCache
        strategy_cache.start_run(tick_cache, tick.timestamp)
        
        # 3. Publish TICK_FLOW_START event
        event_bus.publish("TICK_FLOW_START", tick)
        
        # 4. Workers process and populate cache via strategy_cache
        # ... (event-driven flow via wiring_map)
        
        # 5. Cleanup at end of flow
        strategy_cache.clear()
```

### PlanningWorker Access Pattern

PlanningWorker aggregates signals from cache:

```python
# backend/workers/planning_worker.py
class PlanningWorker:
    def process(self, input_dto):
        # Get all signals from current run
        opportunities = strategy_cache.get_dtos(
            "signals",
            Signal
        )
        
        # Get all risk signals
        threats = strategy_cache.get_dtos(
            "threat_signals",
            Risk
        )
        
        # Decision matrix
        directive = self._create_strategy_directive(
            opportunities,
            threats
        )
        
        return DispositionEnvelope(
            disposition=Disposition.PUBLISH,
            event_name="STRATEGY_DIRECTIVE_READY",
            payload=directive
        )
```

## Testing Strategy

**File:** `tests/unit/core/test_strategy_cache.py`

**Coverage:** 20 comprehensive tests

**Test categories:**
1. Initialization tests (2)
2. start_run() tests (3)
3. get_run_anchor() tests (3)
4. set_dto() tests (3)
5. get_dtos() tests (3)
6. has_dto() tests (3)
7. clear() tests (2)
8. Integration tests (1)

**Key test scenarios:**
- ✅ Cache starts unconfigured
- ✅ start_run() accepts naive/aware datetimes
- ✅ start_run() rejects if already configured
- ✅ All methods raise CacheNotConfiguredError if not configured
- ✅ set_dto() validates Pydantic BaseModel type
- ✅ get_dtos() validates DTO type matches expected
- ✅ has_dto() returns False for missing/empty keys
- ✅ clear() resets to initial state
- ✅ Integration: full lifecycle (start → store → retrieve → clear)

## Error Handling

### Custom Exceptions

```python
# backend/core/interfaces/strategy_cache.py

class CacheNotConfiguredError(RuntimeError):
    """Raised when cache operation attempted before start_run()."""
    pass

class InvalidDTOTypeError(TypeError):
    """Raised when DTO type doesn't match expected type."""
    pass

class CacheAlreadyConfiguredError(ValueError):
    """Raised when start_run() called while cache already configured."""
    pass
```

### Error Scenarios

**1. Calling methods before start_run():**
```python
# ❌ WRONG - cache not configured
anchor = strategy_cache.get_run_anchor()
# Raises: CacheNotConfiguredError
```

**2. Double configuration:**
```python
strategy_cache.start_run(cache1, timestamp1)
strategy_cache.start_run(cache2, timestamp2)  # ❌ Raises ValueError
```

**Fix:** Call `clear()` between runs

**3. Type mismatch:**
```python
strategy_cache.set_dto("signals", "not_a_dto")  # ❌ Raises TypeError
```

**4. Wrong DTO type retrieval:**
```python
# Cache has Signal, but requesting Risk
threats = strategy_cache.get_dtos("signals", Risk)
# ❌ Raises InvalidDTOTypeError
```

## Quality Metrics

| Metric | Value |
|--------|-------|
| **Lines of Code** | ~90 |
| **Tests** | 20 |
| **Test Coverage** | 100% |
| **Pylint Score** | 10.00/10 |
| **Mypy** | 0 errors |
| **Dependencies** | IStrategyCache protocol only |

## Design Decisions

**1. Why Singleton?**
- Single source of truth for current run
- Prevents accidental cache duplication
- Simplifies worker access (no DI needed yet)

**2. Why Separate Protocol?**
- Testability (mock IStrategyCache in worker tests)
- Future: Multiple implementations (Redis cache, distributed cache)
- Separation of concerns (interface vs implementation)

**3. Why RunAnchor?**
- Frozen timestamp prevents mutation
- Type-safe access to run metadata
- Future: Add run_id, strategy_id to RunAnchor

**4. Why TickCache Dictionary?**
- Flexible schema (any DTO key-value)
- No predefined structure needed
- Easy to add new DTO types
- Owned by TickCacheManager (lifecycle management)

## Future Enhancements

**Phase 2: Dependency Injection**
```python
class OpportunityWorker:
    def __init__(self, cache: IStrategyCache):
        self._cache = cache  # Injected, not imported
```

**Phase 3: Distributed Cache**
```python
class RedisStrategyCache(IStrategyCache):
    """Redis-backed implementation for multi-process runs."""
    pass
```

**Phase 4: RunAnchor Extensions**
```python
@dataclass(frozen=True)
class RunAnchor:
    timestamp: datetime
    run_id: str  # Unique run identifier
    strategy_id: str  # Which strategy is running
    backtest_mode: bool  # Live vs backtest
```

## Related Documentation

- **Protocol:** [IStrategyCache Protocol](../../architecture/POINT_IN_TIME_MODEL.md#istrategycache-protocol)
- **Architecture:** [Point-in-Time Model](../../architecture/POINT_IN_TIME_MODEL.md)
- **Architecture:** [No Growing DataFrames Shift](../../architecture/ARCHITECTURAL_SHIFTS.md#shift-2-no-growing-dataframes)
- **Tests:** `tests/unit/core/test_strategy_cache.py`
- **Implementation Status:** [Phase 3.1 Complete](../../implementation/IMPLEMENTATION_STATUS.md)
