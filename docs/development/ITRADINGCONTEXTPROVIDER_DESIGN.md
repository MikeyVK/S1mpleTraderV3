# ITradingContextProvider - Design Document

**Status:** ✅ Multi-Asset Support Added - Ready for Implementation  
**Versie:** 1.1  
**Datum:** 2025-10-28  
**Laatste Update:** Multi-asset cache structure (nested by asset)  
**Gebaseerd op:** V2 Addendum 5.1 (Data Landschap & Point-in-Time Architectuur)

---

## Executive Summary

De **ITradingContextProvider** is de centrale singleton service die DTO-gebaseerde "point-in-time" context beheert en levert aan workers binnen S1mpleTraderV3. Het fungeert als de **poort naar de Tick Cache** - een tijdelijke, type-veilige datastore die alleen bestaat tijdens de verwerking van één enkele tick/flow.

**Kernprincipes:**
1. **Point-in-Time Garantie** - Alle data is gebaseerd op één specifiek moment (tick)
2. **DTO-Centric** - Alleen getypeerde Pydantic DTOs, nooit primitives
3. **Expliciete Dependencies** - Workers declareren hun behoeften via manifest
4. **Type-Safe** - Compiler-enforced contracten via Protocol + generics
5. **Bus-Agnostic Workers** - Workers afhankelijk van interface, niet van implementatie
6. **Multi-Asset Support** - Nested cache structure voor confluence analysis (niet HFT arbitrage)

**Recent Changes (v1.1):**
- ✅ Added `asset: str` parameter to all interface methods
- ✅ Updated `TickCacheType` to nested structure: `Dict[str, Dict[Type[DTO], DTO]]`
- ✅ Added `asset: str` field to `BaseContextDTO`
- ✅ Documented multi-asset use case: confluence analysis across BTC/ETH/altcoins
- ✅ Added cache structure visualization and examples

---

## 1. Architecturale Positie

### 1.1 V2 vs V3 Evolutie

**V2 Model (Verouderd):**
- `TradingContext` met groeiend `enriched_df` (DataFrame)
- Workers muteren gedeelde DataFrame
- Impliciete data-doorgifte via kolommen
- Operators als orkestratie-laag
- Single-asset only

**V3 Model (Huidig):**
- **Minimale BaseContextDTO** (asset, timestamp, current_price)
- **Tick Cache** (Dict[asset, Dict[Type[DTO], DTO]])
- **Expliciete DTO requests** via ITradingContextProvider
- **Direct worker-to-worker** wiring via EventAdapters
- **No Operators** - platgeslagen orkestratie
- **Multi-asset capable** - confluence analysis ready

### 1.2 Levenscyclus & Scope

```
┌──────────────────────────────────────────────────────────────────┐
│ OPERATION SCOPE (Singleton - Leeft hele operation)              │
│                                                                  │
│  ITradingContextProvider (Interface)                             │
│          ↓                                                       │
│  TradingContextProvider (Concrete Singleton)                     │
│          ↓                                                       │
│  ┌────────────────────────────────────────────────────┐         │
│  │ TICK SCOPE (Per tick - Multi-Asset)                │         │
│  │                                                     │         │
│  │  current_tick_cache: TickCacheType = {             │         │
│  │    "BTCUSDT": {                                    │         │
│  │      BaseContextDTO: <instance>,                   │         │
│  │      MarketRegimeDTO: <instance>,                  │         │
│  │      EMAOutputDTO: <instance>                      │         │
│  │    },                                               │         │
│  │    "ETHUSDT": {                                    │         │
│  │      BaseContextDTO: <instance>,                   │         │
│  │      MarketRegimeDTO: <instance>                   │         │
│  │    }                                                │         │
│  │  }                                                  │         │
│  │                                                     │         │
│  │  primary_asset: str  # Last asset from start_tick  │         │
│  │                                                     │         │
│  │  Levensduur: start_new_tick(asset) → (verwerk)     │         │
│  │             → clear_cache()                         │         │
│  └────────────────────────────────────────────────────┘         │
└──────────────────────────────────────────────────────────────────┘
```

**Beheerd door:** TickCacheManager (luistert naar RAW_TICK events)  
**Multi-Asset Flow:** Meerdere `start_new_tick()` calls per tick (één per asset)

---

## 2. Interface Contract (Protocol)

### 2.1 Core Interface

```python
# backend/core/interfaces/trading_context_provider.py

from typing import Protocol, Dict, Type, runtime_checkable
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel

# Type aliases voor leesbaarheid
# Single-asset cache: Dict[Type[DTO], DTO instance]
SingleAssetCacheType = Dict[Type[BaseModel], BaseModel]

# Multi-asset cache: Dict[asset_symbol, SingleAssetCache]
TickCacheType = Dict[str, SingleAssetCacheType]


@runtime_checkable
class ITradingContextProvider(Protocol):
    """
    Protocol voor de service die DTO-gebaseerde 'point-in-time'
    context beheert en levert aan workers.
    
    Levenscyclus:
        1. start_new_tick() - Initieert nieuwe tick cache
        2. get_base_context() - Workers halen minimale context op
        3. get_required_dtos() - Workers halen benodigde DTOs op
        4. set_result_dto() - Workers plaatsen output DTOs
        5. clear_cache() - Cleanup na tick verwerking
    
    Design Principes:
        - Point-in-Time: Alle data behoort bij één specifiek moment
        - Type-Safe: Alleen Pydantic DTOs, compiler-enforced
        - Explicit: Workers declareren behoeften via manifest
        - Immutable Base Context: Timestamp/price nooit wijzigen
    """
    
    def start_new_tick(
        self, 
        tick_cache: TickCacheType,
        timestamp: datetime,
        current_price: Decimal,
        asset: str
    ) -> None:
        """
        Configureert de provider voor een nieuwe tick met een verse cache.
        
        Aangeroepen door: TickCacheManager (bij RAW_TICK event)
        
        Args:
            tick_cache: Lege/bestaande dictionary voor DTO opslag (multi-asset)
            timestamp: Exacte tijdstip van deze tick (UTC)
            current_price: Laatste handelsprijs op dit moment
            asset: Asset identifier (e.g., "BTCUSDT") voor deze tick
            
        Side Effects:
            - Stelt internal current_tick_cache in
            - Creëert BaseContextDTO met timestamp/price voor dit asset
            - Reset alle tick-specifieke state
            - Initialiseert nested cache structure: tick_cache[asset] = {}
            
        Thread Safety:
            - Moet thread-safe zijn (mogelijk meerdere strategieën)
            - Cache per strategie/tick moet geïsoleerd zijn
            
        Multi-Asset Support:
            - Elke start_new_tick call initialiseert één asset in cache
            - Voor multi-asset: meerdere calls met verschillende assets
            - Cache structure: {asset: {Type[DTO]: instance}}
        """
        ...
    
    def get_base_context(self, asset: str | None = None) -> 'BaseContextDTO':
        """
        Haalt de minimale basis context op voor de huidige tick.
        
        Args:
            asset: Asset identifier. Als None, gebruikt primary/laatst ingestelde asset.
                   Voor multi-asset strategies: specificeer expliciet welk asset.
        
        Returns:
            BaseContextDTO met timestamp en current_price voor dit asset
            
        Raises:
            RuntimeError: Als geen actieve tick (start_new_tick not called)
            KeyError: Als gevraagd asset niet in cache (niet geïnitialiseerd)
            
        Usage:
            # Single-asset strategy
            ctx = self.context_provider.get_base_context()
            
            # Multi-asset strategy
            btc_ctx = self.context_provider.get_base_context("BTCUSDT")
            eth_ctx = self.context_provider.get_base_context("ETHUSDT")
            
            # Use context
            df = self.ohlcv_provider.get_window(
                asset=btc_ctx.asset,  # NEW field in BaseContextDTO
                end_time=btc_ctx.timestamp,
                lookback=100
            )
        """
        ...
    
    def get_required_dtos(
        self,
        requesting_worker: 'IWorker',
        dto_types: list[Type[BaseModel]] | None = None,
        asset: str | None = None
    ) -> Dict[Type[BaseModel], BaseModel]:
        """
        Haalt DTO-instanties op die de worker nodig heeft uit de cache.
        
        Args:
            requesting_worker: Worker die DTOs opvraagt (voor logging/validation)
            dto_types: Optionele expliciete lijst. Als None, gebruikt manifest.requires_dtos
            asset: Asset identifier. Als None, gebruikt primary/laatst ingestelde asset.
            
        Returns:
            Dictionary mapping DTO type → DTO instantie (voor opgegeven asset)
            
        Raises:
            MissingContextDataError: Als vereist DTO niet in cache voor dit asset
            InvalidDTOTypeError: Als requested type geen BaseModel is
            KeyError: Als asset niet in cache (niet geïnitialiseerd)
            
        Validation:
            - Checkt of alle requested DTOs in cache[asset] aanwezig zijn
            - Valideert tegen manifest.requires_dtos (als dto_types=None)
            - Logged warning bij missing DTOs voor debugging
            
        Usage:
            # Single-asset worker
            dtos = self.context_provider.get_required_dtos(self)
            ema_data = dtos[EMAOutputDTO]  # Type-safe!
            
            # Multi-asset confluence worker
            btc_dtos = self.context_provider.get_required_dtos(self, asset="BTCUSDT")
            eth_dtos = self.context_provider.get_required_dtos(self, asset="ETHUSDT")
            
            btc_regime = btc_dtos[MarketRegimeDTO]
            eth_momentum = eth_dtos[MomentumDTO]
            # Combine for confluence signal
        """
        ...
    
    def set_result_dto(
        self,
        producing_worker: 'IWorker',
        result_dto: BaseModel,
        asset: str | None = None
    ) -> None:
        """
        Voegt geproduceerd DTO toe aan de cache van de huidige tick.
        
        Args:
            producing_worker: Worker die DTO produceert (for validation)
            result_dto: DTO instantie om op te slaan
            asset: Asset identifier. Als None, gebruikt primary/laatst ingestelde asset.
            
        Side Effects:
            - Voegt result_dto toe aan current_tick_cache[asset]
            - Key = type(result_dto)
            - Overschrijft eerdere DTO van hetzelfde type voor dit asset
            
        Validation:
            - Checkt of result_dto type matched manifest.produces_dtos
            - Valideert dat result_dto een BaseModel is
            - Logged warning bij type mismatch
            
        Raises:
            InvalidDTOTypeError: Als result_dto geen BaseModel
            ValidationError: Als manifest mismatch (strict mode)
            KeyError: Als asset niet in cache (niet geïnitialiseerd)
            
        Usage:
            # Single-asset worker
            self.context_provider.set_result_dto(self, EMAOutputDTO(...))
            
            # Multi-asset worker
            for asset in ["BTCUSDT", "ETHUSDT"]:
                regime = self._calculate_regime(asset)
                self.context_provider.set_result_dto(
                    self, 
                    MarketRegimeDTO(...),
                    asset=asset
                )
        """
        ...
    
    def has_dto(
        self, 
        dto_type: Type[BaseModel],
        asset: str | None = None
    ) -> bool:
        """
        Check of een specifiek DTO type in de cache aanwezig is.
        
        Args:
            dto_type: Type om te checken
            asset: Asset identifier. Als None, gebruikt primary/laatst ingestelde asset.
            
        Returns:
            True als DTO type in cache[asset], anders False
            
        Usage:
            # Single-asset
            if self.context_provider.has_dto(EMAOutputDTO):
                dtos = self.context_provider.get_required_dtos(...)
            
            # Multi-asset optional dependency
            if self.context_provider.has_dto(MarketRegimeDTO, asset="BTCUSDT"):
                btc_regime = self.context_provider.get_required_dtos(
                    self, 
                    dto_types=[MarketRegimeDTO],
                    asset="BTCUSDT"
                )[MarketRegimeDTO]
                # Boost confidence with BTC regime context
        """
        ...
        """
        ...
    
    def clear_cache(self) -> None:
        """
        Ruimt de huidige tick cache op en reset state.
        
        Aangeroepen door: TickCacheManager (na tick verwerking)
        
        Side Effects:
            - Cleart current_tick_cache dictionary
            - Reset base_context naar None
            - Vrijgeeft referenties voor garbage collection
            
        Thread Safety:
            - Moet safe zijn om aan te roepen tijdens actieve tick
            - Nieuwe tick kan direct na clear starten
        """
        ...
```

### 2.2 BaseContextDTO

```python
# backend/dtos/shared/base_context.py

from pydantic import BaseModel, Field
from datetime import datetime
from decimal import Decimal


class BaseContextDTO(BaseModel):
    """
    Minimale basis context voor een tick (per asset).
    
    Bevat ALLEEN de meest essentiële informatie die altijd beschikbaar is.
    Alle andere data wordt on-demand via ITradingContextProvider geleverd.
    
    Design Rationale:
        - Minimaal: Geen bloat, alleen universele timestamp/price/asset
        - Immutable: frozen=True, nooit muteren na creatie
        - Point-in-Time: Timestamp is de anchor voor alle data requests
        - Multi-Asset: Asset identifier voor cross-asset operations
    """
    
    asset: str = Field(
        ...,
        description="Asset identifier (e.g., 'BTCUSDT', 'ETHUSDT'). "
                    "Used for multi-asset strategies and data provider queries."
    )
    
    timestamp: datetime = Field(
        ...,
        description="Exact tijdstip van deze tick (UTC). "
                    "Anchor voor alle point-in-time data requests."
    )
    
    current_price: Decimal = Field(
        ...,
        description="Laatste handelsprijs op dit tijdstip. "
                    "Gebruikt voor PnL berekeningen en validaties.",
        gt=0  # Moet positief zijn
    )
    
    class Config:
        frozen = True  # Immutable
        json_encoders = {
            Decimal: lambda v: str(v)
        }


### 2.3 Multi-Asset Cache Structure

```python
# Voorbeeld cache structuur tijdens multi-asset tick processing

tick_cache: TickCacheType = {
    "BTCUSDT": {
        BaseContextDTO: BaseContextDTO(
            asset="BTCUSDT",
            timestamp=datetime(2025, 10, 28, 14, 30, 0),
            current_price=Decimal("67500.00")
        ),
        MarketRegimeDTO: MarketRegimeDTO(trend="bullish", strength=0.75),
        EMAOutputDTO: EMAOutputDTO(ema_20=67000, ema_50=65000),
        MarketStructureDTO: MarketStructureDTO(bos_detected=True, ...),
    },
    "ETHUSDT": {
        BaseContextDTO: BaseContextDTO(
            asset="ETHUSDT",
            timestamp=datetime(2025, 10, 28, 14, 30, 0),
            current_price=Decimal("3200.00")
        ),
        MarketRegimeDTO: MarketRegimeDTO(trend="neutral", strength=0.45),
        EMAOutputDTO: EMAOutputDTO(ema_20=3180, ema_50=3190),
    },
}

# Confluence worker kan nu cross-asset analysis doen:
btc_regime = tick_cache["BTCUSDT"][MarketRegimeDTO]
eth_regime = tick_cache["ETHUSDT"][MarketRegimeDTO]

if btc_regime.trend == "bullish" and eth_regime.trend == "bullish":
    # Strong confluence signal across major assets
    pass
```

**Cache Lifecycle:**
1. **Start**: TickCacheManager creates empty `{}`
2. **Per Asset**: `start_new_tick(cache, timestamp, price, "BTCUSDT")` → initializes `cache["BTCUSDT"] = {}`
3. **Fill**: ContextWorkers populate `cache[asset][DTOType] = instance`
4. **Read**: OpportunityWorkers read from `cache[asset][DTOType]` (same or different asset)
5. **Clear**: TickCacheManager calls `clear_cache()` → entire dict cleared

---

## 3. Concrete Implementatie

### 3.1 TradingContextProvider Singleton

```python
# backend/core/providers/trading_context_provider.py

from typing import Dict, Type
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel
import logging

from backend.core.interfaces.trading_context_provider import (
    ITradingContextProvider,
    TickCacheType,
    SingleAssetCacheType
)
from backend.dtos.shared.base_context import BaseContextDTO
from backend.core.interfaces.worker import IWorker
from backend.core.exceptions import (
    MissingContextDataError,
    InvalidDTOTypeError,
    NoActiveTickError
)

logger = logging.getLogger(__name__)


class TradingContextProvider(ITradingContextProvider):
    """
    Concrete singleton implementatie van ITradingContextProvider.
    
    Thread Safety:
        - Gebruikt threading.Lock voor cache mutations
        - Separate cache per strategie (via strategy_id key)
        - Safe voor concurrent tick processing
    
    Multi-Asset Support:
        - Cache structure: {asset: {Type[DTO]: instance}}
        - Tracks primary_asset (last asset from start_new_tick)
        - Methods accept optional asset parameter
    
    Lifecycle:
        1. Geïnstantieerd door OperationService (bootstrap)
        2. Geïnjecteerd in alle workers (via WorkerFactory)
        3. Per tick: start_new_tick() → operations → clear_cache()
        4. Leeft voor hele operation duration
    """
    
    def __init__(self):
        """Initialize provider met lege state."""
        self._current_cache: TickCacheType | None = None
        self._base_context: BaseContextDTO | None = None
        self._active_tick_id: str | None = None  # Voor logging/debugging
        
    def start_new_tick(
        self,
        tick_cache: TickCacheType,
        timestamp: datetime,
        current_price: Decimal
    ) -> None:
        """Configure provider voor nieuwe tick."""
        # Validation
        if not isinstance(tick_cache, dict):
            raise TypeError("tick_cache must be a dictionary")
        
        # Reset oude state
        if self._current_cache is not None:
            logger.warning(
                "Previous tick cache was not cleared. "
                "Auto-clearing now (possible memory leak)."
            )
            self.clear_cache()
        
        # Setup nieuwe tick
        self._current_cache = tick_cache
        self._base_context = BaseContextDTO(
            timestamp=timestamp,
            current_price=current_price
        )
        self._active_tick_id = f"{timestamp.isoformat()}_{current_price}"
        
        logger.debug(
            f"Started new tick: {self._active_tick_id}, "
            f"cache size: {len(tick_cache)}"
        )
    
    def get_base_context(self) -> BaseContextDTO:
        """Haal minimale basis context op."""
        if self._base_context is None:
            raise NoActiveTickError(
                "No active tick. Call start_new_tick() first."
            )
        return self._base_context
    
    def get_required_dtos(
        self,
        requesting_worker: IWorker,
        dto_types: list[Type[BaseModel]] | None = None
    ) -> Dict[Type[BaseModel], BaseModel]:
        """Haal benodigde DTOs uit cache."""
        if self._current_cache is None:
            raise NoActiveTickError(
                "No active tick cache. Call start_new_tick() first."
            )
        
        # Determine welke DTOs nodig zijn
        if dto_types is None:
            # Haal uit worker manifest
            dto_types = self._get_required_dto_types_from_manifest(
                requesting_worker
            )
        
        # Validate en retrieve
        result = {}
        missing = []
        
        for dto_type in dto_types:
            if not issubclass(dto_type, BaseModel):
                raise InvalidDTOTypeError(
                    f"{dto_type} is not a Pydantic BaseModel"
                )
            
            if dto_type in self._current_cache:
                result[dto_type] = self._current_cache[dto_type]
            else:
                missing.append(dto_type.__name__)
        
        # Error handling voor missing DTOs
        if missing:
            error_msg = (
                f"Worker {requesting_worker.__class__.__name__} "
                f"missing required DTOs: {', '.join(missing)}. "
                f"Available DTOs: {[t.__name__ for t in self._current_cache.keys()]}"
            )
            logger.error(error_msg)
            raise MissingContextDataError(error_msg)
        
        logger.debug(
            f"Worker {requesting_worker.__class__.__name__} "
            f"retrieved {len(result)} DTOs from cache"
        )
        
        return result
    
    def set_result_dto(
        self,
        producing_worker: IWorker,
        result_dto: BaseModel
    ) -> None:
        """Voeg geproduceerd DTO toe aan cache."""
        if self._current_cache is None:
            raise NoActiveTickError(
                "No active tick cache. Call start_new_tick() first."
            )
        
        # Validation
        if not isinstance(result_dto, BaseModel):
            raise InvalidDTOTypeError(
                f"{type(result_dto)} is not a Pydantic BaseModel"
            )
        
        # Validate tegen manifest (optioneel - kan strict/permissive zijn)
        self._validate_produces_dto(producing_worker, type(result_dto))
        
        # Store in cache (key = DTO type)
        dto_type = type(result_dto)
        self._current_cache[dto_type] = result_dto
        
        logger.debug(
            f"Worker {producing_worker.__class__.__name__} "
            f"produced {dto_type.__name__} to cache. "
            f"Cache size: {len(self._current_cache)}"
        )
    
    def has_dto(self, dto_type: Type[BaseModel]) -> bool:
        """Check DTO aanwezigheid in cache."""
        if self._current_cache is None:
            return False
        return dto_type in self._current_cache
    
    def clear_cache(self) -> None:
        """Ruim tick cache op."""
        if self._current_cache is not None:
            cache_size = len(self._current_cache)
            self._current_cache.clear()
            self._current_cache = None
            self._base_context = None
            
            logger.debug(
                f"Cleared tick cache (had {cache_size} DTOs). "
                f"Tick ID: {self._active_tick_id}"
            )
            self._active_tick_id = None
    
    # --- Helper Methods ---
    
    def _get_required_dto_types_from_manifest(
        self,
        worker: IWorker
    ) -> list[Type[BaseModel]]:
        """
        Extract required DTO types from worker manifest.
        
        Returns:
            List of DTO type classes to retrieve
            
        Implementation Note:
            - Leest worker.manifest.requires_dtos
            - Resolved DTO class names naar actual types
            - Gebruikt DTORegistry voor lookup
        """
        # TODO: Implement manifest parsing
        # Voor nu: assume worker heeft _required_dto_types attribuut
        return getattr(worker, '_required_dto_types', [])
    
    def _validate_produces_dto(
        self,
        worker: IWorker,
        dto_type: Type[BaseModel]
    ) -> None:
        """
        Validate dat produced DTO matched manifest.produces_dtos.
        
        Args:
            worker: Producerende worker
            dto_type: Type van produced DTO
            
        Raises:
            ValidationError: In strict mode bij mismatch
            
        Side Effects:
            - Logged warning bij mismatch (permissive mode)
        """
        # TODO: Implement manifest validation
        # Voor nu: alleen logging
        logger.debug(
            f"Validating {worker.__class__.__name__} "
            f"produces {dto_type.__name__} (validation pending)"
        )
```

---

## 4. Usage Patterns

### 4.1 Worker Bootstrap (Dependency Injection)

```python
# In WorkerFactory tijdens bootstrap

class WorkerFactory:
    def __init__(
        self,
        context_provider: ITradingContextProvider,
        # ... andere providers
    ):
        self._context_provider = context_provider
        # ...
    
    def create_worker(
        self,
        worker_class: Type[IWorker],
        manifest: WorkerManifest
    ) -> IWorker:
        """Create en configure worker instantie."""
        
        # Inject dependencies
        worker = worker_class(
            context_provider=self._context_provider,
            # ... andere providers o.b.v. manifest.requires_capability
        )
        
        return worker
```

### 4.2 Worker Implementation Pattern

```python
# plugins/context/ema_detector/worker.py

from backend.core.interfaces.worker import IWorker
from backend.core.interfaces.trading_context_provider import ITradingContextProvider
from backend.core.interfaces.ohlcv_provider import IOhlcvProvider
from backend.dtos.shared.disposition_envelope import DispositionEnvelope

# Import van centraal geregistreerde DTO
from backend.dto_reg.s1mple/ema_detector/v1_0_0/ema_output_dto import EMAOutputDTO


class EMADetector(IWorker):
    """Context worker die EMA's berekent."""
    
    def __init__(
        self,
        context_provider: ITradingContextProvider,
        ohlcv_provider: IOhlcvProvider
    ):
        # Store geïnjecteerde providers
        self.context_provider = context_provider
        self.ohlcv_provider = ohlcv_provider
    
    def process(self) -> DispositionEnvelope:
        """
        Hoofd processing methode.
        
        Pattern:
            1. Haal base context op
            2. Request platform data (OHLCV)
            3. Execute core logic
            4. Produceer result DTO naar cache
            5. Return flow control envelope
        """
        # 1. Basis context
        ctx = self.context_provider.get_base_context()
        
        # 2. Platform data (point-in-time!)
        df = self.ohlcv_provider.get_window(
            end_time=ctx.timestamp,
            lookback=200  # Genoeg voor EMA 200
        )
        
        # 3. Core logic
        ema_20 = self._calculate_ema(df, period=20)
        ema_50 = self._calculate_ema(df, period=50)
        ema_200 = self._calculate_ema(df, period=200)
        
        # 4. Produceer result DTO
        output = EMAOutputDTO(
            ema_20=ema_20,
            ema_50=ema_50,
            ema_200=ema_200,
            timestamp=ctx.timestamp
        )
        self.context_provider.set_result_dto(self, output)
        
        # 5. Flow control
        return DispositionEnvelope(disposition="CONTINUE")
    
    def _calculate_ema(self, df, period):
        # Implementation...
        pass
```

### 4.3 Consuming Worker Pattern

```python
# plugins/opportunity/ema_cross/worker.py

from backend.core.interfaces.worker import IWorker
from backend.core.interfaces.trading_context_provider import ITradingContextProvider
from backend.dtos.shared.disposition_envelope import DispositionEnvelope
from backend.dtos.strategy.opportunity_signal import OpportunitySignal

# Import required DTO van centrale locatie
from backend.dto_reg.s1mple/ema_detector/v1_0_0.ema_output_dto import EMAOutputDTO


class EMACrossOpportunity(IWorker):
    """Opportunity worker die EMA crosses detecteert."""
    
    # Declare required DTO types (for manifest validation)
    _required_dto_types = [EMAOutputDTO]
    
    def __init__(
        self,
        context_provider: ITradingContextProvider
    ):
        self.context_provider = context_provider
    
    def process(self) -> DispositionEnvelope:
        """
        Detect EMA crosses en publiceer signaal.
        
        Pattern:
            1. Request required DTOs from cache
            2. Execute detection logic
            3. Bij detectie: Return PUBLISH disposition met event
            4. Bij geen detectie: Return STOP
        """
        # 1. Haal benodigde DTOs uit cache
        required_dtos = self.context_provider.get_required_dtos(self)
        ema_data = required_dtos[EMAOutputDTO]
        
        # 2. Detection logic
        cross_detected = (
            ema_data.ema_20 > ema_data.ema_50 and
            # ... previous state check ...
        )
        
        if cross_detected:
            # 3. Publiceer signaal via event
            signal = OpportunitySignal(
                signal_type="ema_cross_bullish",
                confidence=0.75,
                # ... other fields
            )
            
            return DispositionEnvelope(
                disposition="PUBLISH",
                event_name="OPPORTUNITY_DETECTED",
                event_payload=signal
            )
        else:
            # 4. Geen actie
            return DispositionEnvelope(disposition="STOP")
```

---

## 5. Integration met Andere Components

### 5.1 TickCacheManager (Flow Initiator)

```python
# backend/core/tick_cache_manager.py

class TickCacheManager:
    """
    Beheert levenscyclus van tick caches.
    
    Verantwoordelijkheden:
        - Luistert naar RAW_TICK events
        - Creëert verse cache per tick
        - Configureert TradingContextProvider
        - Publiceert TICK_FLOW_START
        - Ruimt cache op na verwerking
    """
    
    def __init__(
        self,
        context_provider: ITradingContextProvider,
        event_bus: IEventBus
    ):
        self.context_provider = context_provider
        self.event_bus = event_bus
    
    def on_raw_tick(self, tick_event: RawTickEvent) -> None:
        """
        Handle nieuwe tick event.
        
        Flow:
            1. Create verse cache
            2. Configure provider
            3. Trigger flow start
            4. (Workers processeren...)
            5. Cleanup cache
        """
        # 1. Create verse cache
        cache: TickCacheType = {}
        
        # 2. Configure provider
        self.context_provider.start_new_tick(
            tick_cache=cache,
            timestamp=tick_event.timestamp,
            current_price=tick_event.price
        )
        
        # 3. Trigger flow
        self.event_bus.publish(
            event_name="TICK_FLOW_START",
            payload=TickFlowStartDTO(
                tick_id=tick_event.tick_id,
                timestamp=tick_event.timestamp
            )
        )
        
        # Note: Cleanup gebeurt via TICK_FLOW_COMPLETE event
        # (zie on_flow_complete methode)
    
    def on_flow_complete(self, complete_event) -> None:
        """Clear cache na afloop van tick processing."""
        self.context_provider.clear_cache()
```

### 5.2 EventAdapter Integration

```python
# EventAdapter roept worker aan, worker gebruikt provider

class EventAdapter:
    """Generieke adapter voor worker communicatie."""
    
    def _invoke_worker(self, worker: IWorker) -> DispositionEnvelope:
        """
        Roep worker processing methode aan.
        
        Note:
            - Worker heeft GEEN EventBus dependency
            - Worker gebruikt ITradingContextProvider voor data
            - Adapter handled DispositionEnvelope routing
        """
        try:
            envelope = worker.process()
            return envelope
        except MissingContextDataError as e:
            # Missing DTOs - log en stop flow
            logger.error(f"Worker {worker} missing data: {e}")
            return DispositionEnvelope(disposition="STOP")
        except Exception as e:
            # Andere errors
            logger.exception(f"Worker {worker} failed: {e}")
            return DispositionEnvelope(disposition="STOP")
```

---

## 6. Testing Strategy

### 6.1 Unit Testing Provider

```python
# tests/unit/core/test_trading_context_provider.py

import pytest
from datetime import datetime, UTC
from decimal import Decimal

from backend.core.providers.trading_context_provider import TradingContextProvider
from backend.core.exceptions import NoActiveTickError, MissingContextDataError


class TestTradingContextProvider:
    """Unit tests for TradingContextProvider."""
    
    @pytest.fixture
    def provider(self):
        """Create fresh provider instance."""
        return TradingContextProvider()
    
    def test_start_new_tick_creates_base_context(self, provider):
        """Test dat start_new_tick base context configureert."""
        # Arrange
        cache = {}
        timestamp = datetime.now(UTC)
        price = Decimal("50000.00")
        
        # Act
        provider.start_new_tick(cache, timestamp, price)
        base_ctx = provider.get_base_context()
        
        # Assert
        assert base_ctx.timestamp == timestamp
        assert base_ctx.current_price == price
    
    def test_get_base_context_raises_without_active_tick(self, provider):
        """Test dat get_base_context faalt zonder actieve tick."""
        # Act & Assert
        with pytest.raises(NoActiveTickError):
            provider.get_base_context()
    
    def test_set_and_get_result_dto_roundtrip(self, provider, mock_worker):
        """Test DTO opslaan en ophalen."""
        # Arrange
        cache = {}
        provider.start_new_tick(cache, datetime.now(UTC), Decimal("50000"))
        
        test_dto = EMAOutputDTO(ema_20=50.0, ema_50=49.5, ema_200=48.0)
        
        # Act
        provider.set_result_dto(mock_worker, test_dto)
        retrieved = provider.get_required_dtos(
            mock_worker,
            dto_types=[EMAOutputDTO]
        )
        
        # Assert
        assert EMAOutputDTO in retrieved
        assert retrieved[EMAOutputDTO] == test_dto
    
    def test_get_required_dtos_raises_when_missing(self, provider, mock_worker):
        """Test dat missing DTOs error geven."""
        # Arrange
        cache = {}
        provider.start_new_tick(cache, datetime.now(UTC), Decimal("50000"))
        
        # Act & Assert
        with pytest.raises(MissingContextDataError):
            provider.get_required_dtos(
                mock_worker,
                dto_types=[EMAOutputDTO]  # Not in cache!
            )
    
    def test_clear_cache_resets_state(self, provider):
        """Test dat clear_cache state reset."""
        # Arrange
        cache = {}
        provider.start_new_tick(cache, datetime.now(UTC), Decimal("50000"))
        
        # Act
        provider.clear_cache()
        
        # Assert
        with pytest.raises(NoActiveTickError):
            provider.get_base_context()
```

### 6.2 Integration Testing (Worker + Provider)

```python
# tests/integration/test_worker_with_provider.py

import pytest
from unittest.mock import Mock

from backend.core.providers.trading_context_provider import TradingContextProvider
from plugins.context.ema_detector.worker import EMADetector


class TestWorkerIntegration:
    """Integration tests voor worker + provider."""
    
    @pytest.fixture
    def setup_environment(self):
        """Setup complete test environment."""
        provider = TradingContextProvider()
        cache = {}
        
        timestamp = datetime.now(UTC)
        price = Decimal("50000.00")
        
        provider.start_new_tick(cache, timestamp, price)
        
        # Mock OHLCV provider
        ohlcv_mock = Mock()
        ohlcv_mock.get_window.return_value = create_test_dataframe()
        
        return provider, ohlcv_mock
    
    def test_ema_detector_produces_dto_to_cache(self, setup_environment):
        """Test dat EMA detector correct DTO produceert."""
        # Arrange
        provider, ohlcv_mock = setup_environment
        worker = EMADetector(
            context_provider=provider,
            ohlcv_provider=ohlcv_mock
        )
        
        # Act
        envelope = worker.process()
        
        # Assert
        assert envelope.disposition == "CONTINUE"
        assert provider.has_dto(EMAOutputDTO)
        
        # Verify DTO inhoud
        dtos = provider.get_required_dtos(worker, [EMAOutputDTO])
        ema_data = dtos[EMAOutputDTO]
        assert ema_data.ema_20 > 0
        assert ema_data.ema_50 > 0
```

---

## 7. Error Handling & Edge Cases

### 7.1 Exception Types

```python
# backend/core/exceptions.py

class ContextProviderError(Exception):
    """Base exception voor provider errors."""
    pass


class NoActiveTickError(ContextProviderError):
    """Raised wanneer operatie vereist actieve tick maar die er niet is."""
    pass


class MissingContextDataError(ContextProviderError):
    """Raised wanneer vereiste DTOs niet in cache zitten."""
    def __init__(self, message: str, missing_types: list[str] | None = None):
        super().__init__(message)
        self.missing_types = missing_types or []


class InvalidDTOTypeError(ContextProviderError):
    """Raised wanneer provided type geen Pydantic BaseModel is."""
    pass
```

### 7.2 Edge Cases

| Scenario | Handling | Rationale |
|----------|----------|-----------|
| start_new_tick() zonder eerst clear_cache() | Auto-clear + warning log | Graceful recovery, prevent memory leak |
| Duplicate DTO type in cache (set_result_dto 2x) | Overschrijft eerdere, log warning | Last-write-wins, maar signal mogelijk bug |
| get_required_dtos() met lege lijst | Return lege dict | Valid use case (worker zonder dependencies) |
| Multiple concurrent ticks (threading) | Separate cache per strategy_id | Prevent cross-contamination |
| Worker crash tijdens tick | Cache blijft in geheugen tot clear_cache() | TickCacheManager moet cleanup forceren |

---

## 8. Performance Considerations

### 8.1 Memory Management

**Tick Cache Lifecycle:**
```
RAW_TICK event
    ↓
Create cache {} (empty dict - ~280 bytes)
    ↓
Workers add DTOs (typical: 5-20 DTOs @ ~1-5KB each)
    ↓
Peak memory: ~10-100KB per tick
    ↓
clear_cache() (end of tick)
    ↓
Garbage collection (Python GC)
```

**Optimization:**
- DTOs zijn immutable (frozen=True) → safe for caching
- Cache cleared elke tick → no accumulation
- Dict lookup is O(1) → fast retrieval

### 8.2 Type Safety Overhead

**Compile-Time:**
- Protocol usage → zero runtime cost
- Type hints → mypy validation only

**Runtime:**
- `isinstance(dto, BaseModel)` check → minimal (<1μs)
- Dict key lookup → O(1)
- DTO validation (Pydantic) → amortized (gebeurt bij creatie)

---

## 9. Open Questions & Future Enhancements

### 9.1 Open Questions

1. **Multi-Strategy Isolation:**
   - Hoe isoleren we caches tussen concurrent draaiende strategieën?
   - Optie A: Separate provider instantie per strategie
   - Optie B: strategy_id als extra key in cache dict
   - **Besluit:** Pending - afhankelijk van multi-strategy support scope

2. **Manifest Validation Timing:**
   - Wanneer valideren we requires_dtos vs produces_dtos?
   - Bootstrap (DependencyValidator) vs Runtime (Provider)?
   - **Voorstel:** Bootstrap voor structure, runtime for sanity checks

3. **DTO Versioning:**
   - Hoe handlen we breaking changes in DTO structure?
   - Centraal DTO register met versie tracking?
   - **Status:** Design pending (zie enrollment exposure mechanisme)

### 9.2 Future Enhancements

**Phase 2 Features:**
- [ ] **Cache Inspection API** - Voor debugging (list all DTOs in cache)
- [ ] **Performance Metrics** - Cache hit/miss rates, DTO sizes
- [ ] **Validation Modes** - Strict vs permissive manifest checking
- [ ] **Multi-Asset Support** - Cache per asset symbol?
- [ ] **Historical Cache Replay** - Voor debugging/testing

**Phase 3 Features:**
- [ ] **DTO Serialization** - Voor persistence/journaling
- [ ] **Cache Compression** - Voor memory efficiency
- [ ] **Async Support** - Voor async workers (future)

---

## 10. Besluitvorming & Next Steps

### 10.1 Design Decisions (Review Needed)

| Beslissing | Status | Notes |
|------------|--------|-------|
| Protocol vs ABC voor interface | ✅ Approved | Protocol = structural typing, flexibeler |
| Dict[Type, DTO] als cache structure | ✅ Approved | Simple, type-safe, O(1) lookup |
| BaseContextDTO minimal (timestamp + price) | ⏳ Review | Is current_price altijd beschikbaar? |
| Auto-clear warning vs exception | ⏳ Review | Graceful vs strict? |
| Manifest validation in provider | ⏳ Review | Provider verantwoordelijkheid of apart component? |

### 10.2 Implementation Roadmap

**Week 1: Core Interface**
- [ ] Implementeer ITradingContextProvider protocol
- [ ] Implementeer BaseContextDTO
- [ ] Implementeer exception types
- [ ] Unit tests voor protocol compliance

**Week 2: Concrete Provider**
- [ ] Implementeer TradingContextProvider singleton
- [ ] start_new_tick() / clear_cache() lifecycle
- [ ] get/set DTO methods met validatie
- [ ] Comprehensive unit tests

**Week 3: Integration**
- [ ] Integreer met TickCacheManager
- [ ] Worker dependency injection via WorkerFactory
- [ ] Integration tests met mock workers
- [ ] Performance testing

**Week 4: Documentation & Examples**
- [ ] API documentation (Sphinx)
- [ ] Worker development guide
- [ ] Troubleshooting guide
- [ ] Migration guide (V2 → V3)

---

## Appendix A: Comparison V2 vs V3

| Aspect | V2 (enriched_df) | V3 (ITradingContextProvider) |
|--------|------------------|-------------------------------|
| **Data Container** | TradingContext.enriched_df (DataFrame) | Tick Cache (Dict[Type, DTO]) |
| **Data Format** | Kolommen in DataFrame | Getypeerde DTOs |
| **Data Passing** | Implicitly via DataFrame mutatie | Explicitly via provider methods |
| **Type Safety** | Runtime (kolom naam strings) | Compile-time (DTO types) |
| **Dependencies** | Implicitly (kolom aanwezigheid) | Explicitly (manifest.requires_dtos) |
| **Lifecycle** | Groeiend per tick | Fresh per tick |
| **Memory** | Accumulative | Bounded per tick |
| **Testing** | Mock DataFrame | Mock provider + DTOs |
| **Debugging** | DataFrame inspect | Cache inspection |

---

## Appendix B: Complete Code Example

Zie: `examples/trading_context_provider_usage.py` (TODO)

---

**Document Owner:** Architecture Team  
**Review Status:** Draft - Awaiting Review  
**Last Updated:** 2025-10-28
