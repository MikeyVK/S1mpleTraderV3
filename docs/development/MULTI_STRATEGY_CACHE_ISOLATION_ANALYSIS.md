# Multi-Strategy Cache Isolation - Trade-off Analysis

**Status:** Decision Needed  
**Datum:** 2025-10-28  
**Gerelateerd aan:** ITradingContextProvider Design (§9.1 - Open Question #1)

---

## Executive Summary

**Centrale Vraag:** Hoe isoleren we tick caches tussen concurrent draaiende strategieën?

**Twee Opties:**
- **Optie A:** Separate `ITradingContextProvider` instantie per strategie
- **Optie B:** Shared provider met `strategy_id` als cache key

Deze beslissing beïnvloedt:
- Thread safety complexity
- Memory overhead
- Worker injection patterns
- Testing & debugging
- Multi-strategy operation architecture

---

## 1. Context: Multi-Strategy Operations

### 1.1 Use Case uit V2 Architecture

Uit `operation.yaml` (§4.4.1):
```yaml
# config/operations/multi_strategy_operation.yaml
display_name: "Multi-Strategy Test"
description: "Runs ICT/SMC strategy live and backtests a DCA strategy"
strategy_links:
  - strategy_blueprint_id: "ict_smc_strategy"
    execution_environment_id: "live_kraken_main"
    is_active: true
  
  - strategy_blueprint_id: "smart_dca_btc"
    execution_environment_id: "backtest_2024_q1"
    is_active: true
```

**Implicatie:**
- Twee strategieën draaien **tegelijkertijd** in dezelfde operation
- Elke strategie heeft eigen workforce (workers)
- Elke strategie verwerkt **eigen ticks** (kan zelfde asset zijn!)
- Strategieën mogen **niet elkaars cache vervuilen**

### 1.2 Tick Processing Flow (Concurrent)

```
TIME: 14:30:00
    ↓
RAW_TICK event (BTCUSDT @ $67500)
    ↓
    ├─→ ICT Strategy:
    │    - ContextWorkers process → DTOs in cache
    │    - OpportunityWorkers read cache → OpportunitySignals
    │    - Planning/Execution...
    │
    └─→ DCA Strategy:
         - ContextWorkers process → DTOs in cache
         - ThreatWorkers read cache → ThreatSignals
         - Planning/Execution...

BEIDE strategieën verwerken DEZELFDE tick, maar met EIGEN context!
```

**Kritisch Punt:**
- ICT strategy gebruikt `FVGDetector`, `MarketStructureDetector`
- DCA strategy gebruikt `RegimeClassifier`, `RiskAssessor`
- Beide produceren `MarketRegimeDTO` → **CONFLICT** als cache gedeeld!

---

## 2. Optie A: Separate Provider Instantie per Strategie

### 2.1 Architectuur

```python
# OperationService bootstrap

for strategy_link in operation.strategy_links:
    # Elke strategie krijgt EIGEN provider instantie
    strategy_provider = TradingContextProvider()
    
    # Workers krijgen provider geïnjecteerd via factory
    workforce = WorkerFactory.create_workforce(
        blueprint=strategy_link.blueprint,
        context_provider=strategy_provider,  # <-- DEDICATED
        # ... other providers
    )
    
    # Store per strategy
    strategy_runs[strategy_link.id] = {
        "provider": strategy_provider,
        "workforce": workforce,
        "tick_cache_manager": TickCacheManager(strategy_provider)
    }
```

### 2.2 Cache Structure (Per Strategie)

```python
# ICT Strategy - Provider Instance #1
ict_provider.current_tick_cache = {
    "BTCUSDT": {
        BaseContextDTO: <instance>,
        MarketRegimeDTO: <regime from ICT perspective>,
        FVGOutputDTO: <FVG patterns>,
        MarketStructureDTO: <BOS/CHoCH>,
        LiquidityZonesDTO: <buy/sell liquidity>
    }
}

# DCA Strategy - Provider Instance #2  
dca_provider.current_tick_cache = {
    "BTCUSDT": {
        BaseContextDTO: <instance>,
        MarketRegimeDTO: <regime from DCA perspective>,  # DIFFERENT!
        RiskAssessmentDTO: <portfolio risk>,
        VolatilityDTO: <market volatility>
    }
}

# GEEN conflict - volledig geïsoleerd!
```

### 2.3 Worker Injection

```python
# Worker krijgt provider via constructor
class EMADetector(ContextWorker):
    def __init__(
        self,
        context_provider: ITradingContextProvider,  # <-- Injected
        ohlcv_provider: IOhlcvProvider,
        **params
    ):
        self._context_provider = context_provider
        self._ohlcv = ohlcv_provider
        self._params = params
```

**Voordeel:** Worker weet NIET tot welke strategie hij behoort → pure business logic

### 2.4 Voordelen ✅

| Voordeel | Rationale |
|----------|-----------|
| **Perfect Isolation** | Elke strategie heeft eigen geheugenruimte - zero cross-contamination |
| **Zero Thread Complexity** | Geen shared state → geen locks/mutexes nodig |
| **Simple Worker Code** | Worker roept gewoon `self._context_provider.get_required_dtos()` - geen strategy_id |
| **Independent Lifecycle** | Elke strategie kan start/stop onafhankelijk |
| **Easy Testing** | Mock één provider per test - geen strategy_id setup |
| **Memory Predictable** | Elke strategie: ~10-100KB cache - lineair schaalt met aantal strategieën |
| **No Leakage Risk** | Provider crash in strategy A raakt B niet |
| **Clean Shutdown** | Strategy stop → provider cleanup automatisch |

### 2.5 Nadelen ❌

| Nadeel | Impact | Mitigatie |
|--------|--------|-----------|
| **Memory Overhead** | Elke provider ~280 bytes base + cache | Verwaarloosbaar (<1KB per strategie) |
| **More Instances** | N strategieën = N providers | Acceptabel (singletons zijn lightweight) |
| **Cross-Strategy Sharing Impossible** | Strategy A kan B's cache NOOIT zien | **Is dit een nadeel?** → Design question |
| **Potential Code Duplication** | Als provider logic complex wordt | YAGNI - provider is dun wrapper |

### 2.6 Implementation Pattern

```python
# backend/core/providers/trading_context_provider.py

class TradingContextProvider(ITradingContextProvider):
    """
    Concrete provider - PER STRATEGIE geïnstantieerd.
    
    GEEN strategy_id tracking - provider "weet" niet tot welke
    strategie hij behoort. Pure data service.
    """
    
    def __init__(self):
        """Lightweight - geen heavy resources."""
        self._current_tick_cache: TickCacheType = {}
        self._primary_asset: str | None = None
        self._lock = threading.Lock()  # Voor deze instantie only
    
    def start_new_tick(self, tick_cache, timestamp, price, asset):
        with self._lock:  # Thread-safe voor DEZE strategie
            # ... initialize cache[asset]
```

**Key Point:** Provider heeft GEEN `strategy_id` field - volledig agnostisch!

---

## 3. Optie B: Shared Provider met strategy_id Key

### 3.1 Architectuur

```python
# OperationService bootstrap

# ÉÉN shared provider voor ALLE strategieën
shared_provider = TradingContextProvider()

for strategy_link in operation.strategy_links:
    # Workers krijgen ZELFDE provider + strategy_id
    workforce = WorkerFactory.create_workforce(
        blueprint=strategy_link.blueprint,
        context_provider=shared_provider,  # <-- SHARED!
        strategy_id=strategy_link.id,      # <-- NEW!
        # ... other providers
    )
    
    strategy_runs[strategy_link.id] = {
        "workforce": workforce,
        # Provider is shared - geen aparte referentie
    }
```

### 3.2 Cache Structure (Shared)

```python
# ÉÉN provider met geneste caches
shared_provider.current_tick_cache = {
    "ict_strategy": {  # <-- Strategy ID als key
        "BTCUSDT": {
            BaseContextDTO: <instance>,
            MarketRegimeDTO: <ICT regime>,
            FVGOutputDTO: <...>,
        }
    },
    "dca_strategy": {  # <-- Aparte namespace
        "BTCUSDT": {
            BaseContextDTO: <instance>,
            MarketRegimeDTO: <DCA regime>,
            RiskAssessmentDTO: <...>,
        }
    }
}
```

**Type Signature:**
```python
# Optie A
TickCacheType = Dict[str, Dict[Type[DTO], DTO]]
#                    ^asset  ^type       ^instance

# Optie B
TickCacheType = Dict[str, Dict[str, Dict[Type[DTO], DTO]]]
#                    ^strategy ^asset ^type       ^instance
```

### 3.3 Worker Changes (Breaking!)

```python
class EMADetector(ContextWorker):
    def __init__(
        self,
        context_provider: ITradingContextProvider,
        strategy_id: str,  # <-- NEW REQUIRED PARAMETER!
        ohlcv_provider: IOhlcvProvider,
        **params
    ):
        self._context_provider = context_provider
        self._strategy_id = strategy_id  # <-- Must track!
        self._ohlcv = ohlcv_provider
    
    def process(self) -> DispositionEnvelope:
        # MUST pass strategy_id to every provider call
        ctx = self._context_provider.get_base_context(
            asset="BTCUSDT",
            strategy_id=self._strategy_id  # <-- Extra param!
        )
        
        dtos = self._context_provider.get_required_dtos(
            self,
            strategy_id=self._strategy_id  # <-- Everywhere!
        )
```

**Implicatie:** **ELKE provider method** krijgt `strategy_id` parameter!

### 3.4 Interface Changes

```python
@runtime_checkable
class ITradingContextProvider(Protocol):
    def start_new_tick(
        self,
        tick_cache: TickCacheType,
        timestamp: datetime,
        current_price: Decimal,
        asset: str,
        strategy_id: str  # <-- NEW!
    ) -> None: ...
    
    def get_base_context(
        self,
        asset: str | None = None,
        strategy_id: str | None = None  # <-- NEW!
    ) -> BaseContextDTO: ...
    
    def get_required_dtos(
        self,
        requesting_worker: IWorker,
        dto_types: list[Type[BaseModel]] | None = None,
        asset: str | None = None,
        strategy_id: str | None = None  # <-- NEW!
    ) -> Dict[Type[BaseModel], BaseModel]: ...
    
    # ... same for set_result_dto, has_dto
```

**Implicatie:** Interface wordt complexer!

### 3.5 Voordelen ✅

| Voordeel | Rationale |
|----------|-----------|
| **Single Instance** | Slechts 1 provider object - marginaal minder memory |
| **Centralized Control** | Alle cache operations via 1 object - eenvoudiger monitoring? |
| **Cross-Strategy Inspection** | Strategy A zou B's cache kunnen inspecteren (debugging?) |
| **Shared Infrastructure** | Locks, logging, metrics in 1 plek |

### 3.6 Nadelen ❌

| Nadeel | Impact | Severity |
|--------|--------|----------|
| **Thread Contention** | Alle strategieën concurreren om `_lock` | 🔴 HIGH - Performance bottleneck |
| **Complex Locking** | Moet strategy-level granular locks implementeren | 🔴 HIGH - Bug risk |
| **Worker Pollution** | Workers moeten strategy_id tracken | 🔴 HIGH - Violates SRP |
| **Interface Bloat** | Elke method krijgt `strategy_id` param | 🟡 MEDIUM - API complexity |
| **Error Propagation** | Bug in cache logic raakt ALLE strategieën | 🔴 HIGH - Blast radius |
| **Testing Complexity** | Moet multi-strategy setup in elke test | 🟡 MEDIUM - Test overhead |
| **Memory Leak Risk** | Vergeten strategy_id cleanup = leak ALL strategies | 🔴 HIGH - Operational risk |
| **Debugging Harder** | Cache dumps bevatten ALLE strategieën - noise | 🟡 MEDIUM - DX impact |

### 3.7 Thread Safety Hell

```python
class TradingContextProvider:
    def __init__(self):
        # Optie 1: Global lock (BAD - serializes everything)
        self._global_lock = threading.Lock()
        
        # Optie 2: Per-strategy locks (COMPLEX)
        self._strategy_locks: Dict[str, threading.Lock] = {}
        
        # Optie 3: Read-write lock (OVERKILL)
        self._rwlock = ReadWriteLock()
    
    def get_required_dtos(self, worker, strategy_id, ...):
        # Welke lock gebruiken we?
        # Global lock = slow (blocks all strategies)
        # Per-strategy = complex (lock management hell)
        
        with self._get_lock_for_strategy(strategy_id):  # Ugh!
            # ... fetch from cache[strategy_id][asset][type]
```

**Probleem:** Concurrent tick processing van 2+ strategieën wordt serialized!

---

## 4. Vergelijkingstabel

| Aspect | Optie A (Separate) | Optie B (Shared) |
|--------|-------------------|------------------|
| **Memory per Strategy** | ~10-100KB + 280 bytes base | ~10-100KB (base amortized) |
| **Total Memory (3 strategies)** | ~30-300KB + 840 bytes | ~30-300KB + 280 bytes |
| **Thread Safety** | ✅ Zero contention (isolated) | ❌ Complex locking required |
| **Worker Code Complexity** | ✅ Simple (`self._provider`) | ❌ Track `strategy_id` everywhere |
| **Interface Complexity** | ✅ Clean (6 methods, no strategy_id) | ❌ Bloated (every method +1 param) |
| **Bug Blast Radius** | ✅ Isolated (strategy A crash ≠ B) | ❌ Shared (one bug → all down) |
| **Testing** | ✅ Simple (mock 1 provider) | ❌ Complex (multi-strategy setup) |
| **Cross-Strategy Sharing** | ❌ Impossible | ✅ Mogelijk (maar is dit een feature?) |
| **Performance** | ✅ Parallel processing (zero locks) | ❌ Lock contention (serialization) |
| **Memory Leak Risk** | ✅ Low (strategy cleanup = auto) | ❌ High (manual strategy_id cleanup) |
| **Debugging** | ✅ Clean dumps (1 strategy/cache) | ❌ Noisy dumps (all strategies) |
| **Implementation LOC** | ~200 lines | ~350 lines (locking + strategy management) |

---

## 5. Real-World Scenario Analysis

### Scenario 1: Standard Multi-Strategy Backtest

**Setup:**
- 3 strategieën draaien concurrent
- Zelfde asset (BTCUSDT)
- Different timeframes (1m, 5m, 15m)

**Optie A:**
```python
# Clean - elke strategie onafhankelijk
for strategy in strategies:
    strategy.tick_manager.process_tick(timestamp, price, "BTCUSDT")
    # → Eigen cache, zero interference
```

**Optie B:**
```python
# Complex - moet strategy_id propageren
for strategy in strategies:
    strategy.tick_manager.process_tick(
        timestamp, price, "BTCUSDT",
        strategy_id=strategy.id  # Extra param!
    )
    # → Shared cache met locks
```

**Winner:** 🏆 Optie A

---

### Scenario 2: Cross-Strategy Signal Correlation (Hypothetical)

**Use Case:** "Neem alleen ICT entries als DCA strategy bullish is"

**Optie A:**
```python
# Moet expliciet signaling tussen strategieën bouwen
# Via EventBus of shared state mechanism
ict_worker.process():
    # Check DCA regime via custom mechanism
    if dca_strategy.get_regime() == "bullish":  # External API
        # ... enter
```

**Optie B:**
```python
# Kan direct andere strategy cache lezen
ict_worker.process():
    dca_regime = self._provider.get_required_dtos(
        self,
        dto_types=[MarketRegimeDTO],
        strategy_id="dca_strategy"  # Cross-strategy read!
    )[MarketRegimeDTO]
```

**Winner:** 🏆 Optie B (maar is dit een gewenste feature?)

**Counterpoint:** Cross-strategy coupling is **anti-pattern**!
- Strategies moeten onafhankelijk zijn (single responsibility)
- Als correlatie nodig: bouw aparte "meta-strategy" die beide monitort

---

### Scenario 3: Memory-Constrained Environment (Edge Device)

**Setup:**
- Raspberry Pi met 1GB RAM
- 10 strategieën draaien

**Optie A:**
- 10 providers × 280 bytes = 2.8 KB base overhead
- 10 caches × ~50 KB = 500 KB total

**Optie B:**
- 1 provider × 280 bytes = 280 bytes base overhead
- 1 cache × 10 strategies × ~50 KB = 500 KB total

**Verschil:** **2.5 KB** (0.0025% of 1GB RAM)

**Winner:** 🤝 TIE (verwaarloosbaar verschil)

---

## 6. Design Principles Analysis

### 6.1 Single Responsibility Principle (SRP)

**Worker Responsibility:** "Proces tick data en produceer DTO"

**Optie A:**
```python
class Worker:
    def process(self):
        # Focus ONLY on business logic
        dtos = self._provider.get_required_dtos(self)
        # No awareness of multi-strategy context
```
✅ **Worker kent ALLEEN zijn eigen domein**

**Optie B:**
```python
class Worker:
    def process(self):
        # Must track strategy identity
        dtos = self._provider.get_required_dtos(self, strategy_id=self._strategy_id)
        # Polluted with infrastructure concern
```
❌ **Worker moet strategy isolation managen**

**Winner:** 🏆 Optie A

---

### 6.2 Dependency Inversion Principle (DIP)

**Principe:** "Depend on abstractions, not concretions"

**Optie A:**
```python
# Worker depends on ITradingContextProvider (interface)
# No knowledge of multi-strategy implementation
worker = Worker(context_provider=provider)  # Clean injection
```
✅ **Pure interface dependency**

**Optie B:**
```python
# Worker depends on ITradingContextProvider + strategy_id concept
# Leaks multi-strategy implementation detail into interface
worker = Worker(
    context_provider=provider,
    strategy_id="ict_strategy"  # Infrastructure leak!
)
```
❌ **Interface leaks implementation**

**Winner:** 🏆 Optie A

---

### 6.3 Separation of Concerns

**Concern 1:** "Manage tick cache lifecycle"  
**Concern 2:** "Isolate multi-strategy execution"

**Optie A:**
- Concern 1: `TradingContextProvider` (focus ONLY on cache)
- Concern 2: `OperationService` (manages provider instances)
✅ **Separated**

**Optie B:**
- Concern 1 + 2: `TradingContextProvider` (does BOTH)
❌ **Mixed**

**Winner:** 🏆 Optie A

---

## 7. Implementation Effort

### Optie A

**New Code:**
```python
# backend/core/providers/trading_context_provider.py (200 lines)
# No strategy_id logic needed!

class TradingContextProvider(ITradingContextProvider):
    def __init__(self):
        self._current_tick_cache: TickCacheType = {}
        self._lock = threading.Lock()
    
    # ... 6 methods, no strategy_id parameter
```

**Bootstrap:**
```python
# services/operation_service.py
for strategy_link in operation.strategy_links:
    provider = TradingContextProvider()  # Simple!
    # ... inject into workers
```

**Testing:**
```python
def test_worker():
    provider = TradingContextProvider()
    worker = Worker(context_provider=provider)
    # Simple!
```

**Effort:** 🟢 **2-3 dagen**

---

### Optie B

**New Code:**
```python
# backend/core/providers/trading_context_provider.py (350+ lines)
# Complex strategy_id tracking + locking!

class TradingContextProvider(ITradingContextProvider):
    def __init__(self):
        self._current_tick_cache: Dict[str, TickCacheType] = {}
        self._strategy_locks: Dict[str, threading.Lock] = {}
        self._global_lock = threading.Lock()
    
    def _get_or_create_lock(self, strategy_id: str):
        # Lock management hell
        with self._global_lock:
            if strategy_id not in self._strategy_locks:
                self._strategy_locks[strategy_id] = threading.Lock()
            return self._strategy_locks[strategy_id]
    
    # ... 6 methods, each with strategy_id parameter + locking logic
```

**Worker Changes:**
```python
# ALLE workers moeten strategy_id tracken
class BaseWorker:
    def __init__(self, strategy_id: str, ...):  # Breaking change!
        self._strategy_id = strategy_id
```

**Testing:**
```python
def test_worker():
    provider = TradingContextProvider()
    worker = Worker(
        context_provider=provider,
        strategy_id="test_strategy"  # Extra setup!
    )
    # More complex!
```

**Effort:** 🔴 **5-7 dagen** (complexer + breaking changes)

---

## 8. Recommendation

### 🏆 **OPTIE A: Separate Provider Instance per Strategie**

**Rationale:**

1. **Perfect Isolation** - Zero cross-contamination, zero thread contention
2. **Simple Worker Code** - Workers blijven focused op business logic
3. **Clean Interface** - Geen strategy_id pollution
4. **Better Design** - Follows SRP, DIP, separation of concerns
5. **Easier Testing** - Simple mocks, no multi-strategy setup
6. **Lower Risk** - Bug blast radius beperkt tot 1 strategie
7. **Better Performance** - Parallel processing zonder locks
8. **Negligible Overhead** - 2.8 KB voor 10 strategieën is verwaarloosbaar

**Trade-off Accepted:**
- Cross-strategy cache sharing impossible → **GOOD!** (Anti-pattern anyway)
- Marginaal meer memory → **Irrelevant** (< 0.01% impact)

---

## 9. Implementation Plan (Optie A)

### Phase 1: Provider Implementation
```python
# backend/core/providers/trading_context_provider.py

class TradingContextProvider(ITradingContextProvider):
    """
    Per-strategy singleton provider.
    
    GEEN strategy_id tracking - provider is strategy-agnostic.
    Isolation gebeurt door separate instances.
    """
    
    def __init__(self):
        self._current_tick_cache: TickCacheType = {}
        self._primary_asset: str | None = None
        self._lock = threading.Lock()  # For THIS instance only
```

### Phase 2: OperationService Bootstrap
```python
# services/operation_service.py

class OperationService:
    def _bootstrap_strategy_link(self, link: StrategyLink):
        # Create DEDICATED provider
        strategy_provider = TradingContextProvider()
        
        # Inject into all platform providers
        providers = {
            "context_provider": strategy_provider,
            "ohlcv_provider": ...,
            "ledger_provider": ...,
        }
        
        # Create workforce with injected provider
        workforce = WorkerFactory.create_workforce(
            blueprint=link.blueprint,
            **providers
        )
        
        # Store per strategy
        self._strategy_runs[link.id] = {
            "provider": strategy_provider,
            "workforce": workforce,
            "tick_manager": TickCacheManager(strategy_provider)
        }
```

### Phase 3: Worker Injection (No Changes!)
```python
# Workers blijven simpel - GEEN strategy_id!
class EMADetector(ContextWorker):
    def __init__(
        self,
        context_provider: ITradingContextProvider,  # Injected
        ohlcv_provider: IOhlcvProvider,
        **params
    ):
        self._context_provider = context_provider
        # NO strategy_id tracking needed!
```

---

## 10. Decision

**BESLUIT:** Implement **Optie A - Separate Provider per Strategie**

**Justification:**
- Superior design (SRP, DIP, separation of concerns)
- Better performance (zero lock contention)
- Simpler implementation (200 vs 350 LOC)
- Lower risk (isolated failures)
- Negligible memory overhead

**Rejected Alternative:** Optie B (Shared provider)
- Violates SRP (workers track strategy_id)
- Performance bottleneck (global locking)
- Higher complexity (lock management)
- Larger blast radius (shared failure)
- No compelling benefits (cross-strategy sharing is anti-pattern)

---

**Document Owner:** Architecture Team  
**Status:** ✅ Decision Made - Ready for Implementation  
**Last Updated:** 2025-10-28
