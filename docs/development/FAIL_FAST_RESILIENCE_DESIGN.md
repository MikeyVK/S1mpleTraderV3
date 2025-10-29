# Manifest-Driven Resource Validation & Fail-Fast Resilience

**Status:** Design Decision  
**Datum:** 2025-10-28  
**Gerelateerd aan:** ITradingContextProvider Design - Questions #4, #5, #6

---

## Executive Summary

**Beslissing #4:** BaseContextDTO wordt **capability-driven** in plaats van optional fields.

**Beslissing #5:** **Fail-Fast** bij missing resources/dependencies.

**Beslissing #6:** Manifest validation gebeurt bij **BOOTSTRAP (DependencyValidator)** én **RUNTIME (Provider)**.

**Impact op ITradingContextProvider:**
- Interface methoden krijgen **NO optional parameters** (fails zijn exceptions, niet None)
- TickCache blijft **simpel** (geen fallback/degradation logic)
- Workers krijgen **guaranteed contracts** (als bootstrap slaagt, runtime altijd correct)

---

## 1. Manifest-Driven Capability System (SIMPLIFIED)

### 1.1 Worker Manifest - Capabilities Only

```yaml
# plugins/momentum_signal/manifest.yaml

identification:
  name: "momentum_signal"
  type: "opportunity_worker"
  subtype: "momentum_signal"

# === SYSTEM RESOURCES: What does this worker NEED? ===
requires_system_resources:
  capabilities:
    - "ohlcv_window"       # Platform must provide OHLCV data
    - "realtime_price"     # Platform must provide current tick price
    - "tick_volume"        # Platform must provide tick volume
  
  context_dtos:
    critical:
      - "EMAOutputDTO"         # MUST be in cache (bootstrap fails if no producer)
      - "MarketRegimeDTO"      # MUST be in cache
    optional:
      - "ATROutputDTO"         # Nice-to-have (worker degrades gracefully if absent)

produces_dtos:
  - "MomentumSignalDTO"

# NO flow_type declarations!
# Worker is agnostic - platform decides if it can satisfy requirements
```

**Rationale:**
- Worker declares **WHAT** it needs, not **WHEN** it runs
- Platform determines compatibility based on **available capabilities**
- Trigger source (tick/news/schedule) is **platform implementation detail**
- Same worker can run in different contexts if capabilities are met

### 1.2 Capability Registry (Platform-Side)

```python
# backend/core/capability_registry.py

from typing import Protocol, Set
from dataclasses import dataclass

@dataclass(frozen=True)
class TriggerContext:
    """
    What triggered this strategy run.
    
    This is a PLATFORM CONCEPT - workers don't need to know.
    Used for journaling and debugging only.
    """
    trigger_type: str  # "market_tick" | "news_event" | "scheduled_task" | "manual"
    trigger_id: str    # tick_id | news_id | schedule_id | user_id
    metadata: dict     # Type-specific data

class ICapabilityProvider(Protocol):
    """Platform provider that exposes a capability."""
    
    @property
    def provides_capability(self) -> str:
        """Capability identifier (e.g., 'realtime_price')."""
        ...
    
    def is_available(self, trigger_context: TriggerContext) -> bool:
        """
        Check if this capability is available given the trigger context.
        
        Example:
        - RealtimePriceProvider.is_available() checks if trigger has fresh price
        - OhlcvProvider.is_available() always returns True (historical data)
        """
        ...

class CapabilityRegistry:
    """
    Central registry of platform capabilities.
    
    Maps capability names → providers.
    Used for bootstrap validation.
    """
    
    def __init__(self):
        self._providers: dict[str, ICapabilityProvider] = {}
    
    def register(self, provider: ICapabilityProvider) -> None:
        """Register a capability provider."""
        self._providers[provider.provides_capability] = provider
    
    def get_available_capabilities(
        self, 
        trigger_context: TriggerContext
    ) -> Set[str]:
        """
        Get capabilities available for given trigger context.
        
        Example:
        - market_tick trigger → {"realtime_price", "ohlcv_window", "market_depth"}
        - news_event trigger → {"ohlcv_window", "news_metadata"}
        - scheduled_task trigger → {"ohlcv_window", "ledger_state"}
        """
        return {
            cap_name
            for cap_name, provider in self._providers.items()
            if provider.is_available(trigger_context)
        }
    
    def supports_capability(self, capability: str) -> bool:
        """Check if capability is registered (regardless of trigger)."""
        return capability in self._providers
    
    def validate_requirements(
        self,
        required_capabilities: list[str],
        trigger_context: TriggerContext
    ) -> list[str]:
        """
        Get list of required capabilities NOT available in trigger context.
        
        Returns:
            List of missing capability names (empty if all satisfied)
        """
        available = self.get_available_capabilities(trigger_context)
        return [cap for cap in required_capabilities if cap not in available]
```

**Key Insight:**
- Worker manifest: `requires_capabilities: ["realtime_price"]`
- Platform decides: "Can I provide realtime_price for THIS trigger?"
- NO hardcoded flow type checks in worker code!

---

## 2. Bootstrap Validation (Simplified)

### 2.1 Validation Flow

```python
# backend/assembly/dependency_validator.py

from typing import List
from backend.config.schemas.strategy_blueprint import StrategyBlueprint
from backend.config.schemas.operation_config import TriggerConfig
from backend.core.capability_registry import CapabilityRegistry, TriggerContext
from backend.assembly.plugin_registry import PluginRegistry

class DependencyValidator:
    """
    Validates strategy configuration at BOOTSTRAP.
    
    Simplified approach:
    1. Check which triggers are configured for this operation
    2. For each trigger, check if ALL workers' capabilities can be satisfied
    3. Validate DTO dependency chains
    
    NO flow type abstractions - just capabilities!
    """
    
    def __init__(
        self, 
        plugin_registry: PluginRegistry,
        capability_registry: CapabilityRegistry
    ):
        self._plugins = plugin_registry
        self._capabilities = capability_registry
    
    def validate_strategy(
        self,
        blueprint: StrategyBlueprint,
        trigger_configs: list[TriggerConfig]  # From operation.yaml
    ) -> ValidationResult:
        """
        Full validation of strategy dependencies.
        
        Args:
            blueprint: Strategy configuration (workforce, etc.)
            trigger_configs: List of triggers that will invoke this strategy
        
        Returns:
            ValidationResult with errors/warnings
        
        Raises:
            ConfigurationError: If critical dependencies cannot be satisfied
        """
        errors = []
        warnings = []
        
        # 1. For EACH trigger, validate ALL workers can run
        for trigger_config in trigger_configs:
            trigger_ctx = self._build_trigger_context(trigger_config)
            
            self._validate_trigger_compatibility(
                blueprint, 
                trigger_ctx, 
                errors, 
                warnings
            )
        
        # 2. Validate DTO dependencies (trigger-agnostic)
        self._validate_dto_dependencies(blueprint, errors, warnings)
        
        if errors:
            raise ConfigurationError(
                f"Strategy validation failed with {len(errors)} errors:\n" +
                "\n".join(f"- {e}" for e in errors)
            )
        
        return ValidationResult(errors=[], warnings=warnings)
    
    def _validate_trigger_compatibility(
        self,
        blueprint: StrategyBlueprint,
        trigger_context: TriggerContext,
        errors: List[str],
        warnings: List[str]
    ):
        """Validate that all workers can run given this trigger context."""
        
        # Get available capabilities for this trigger
        available_caps = self._capabilities.get_available_capabilities(trigger_context)
        
        # Check EACH worker's requirements
        for worker_config in blueprint.workforce.all_workers():
            manifest = self._plugins.get_manifest(worker_config.plugin)
            
            required_caps = manifest.requires_system_resources.capabilities
            missing_caps = [cap for cap in required_caps if cap not in available_caps]
            
            if missing_caps:
                errors.append(
                    f"Worker '{worker_config.plugin}' requires capabilities {missing_caps} "
                    f"which are NOT available for trigger '{trigger_context.trigger_type}'. "
                    f"Available: {sorted(available_caps)}. "
                    f"Either remove worker or remove this trigger from operation config."
                )
    
    def _build_trigger_context(self, trigger_config: TriggerConfig) -> TriggerContext:
        """Convert trigger config to context for capability checking."""
        return TriggerContext(
            trigger_type=trigger_config.type,  # "market_tick" | "news_event" | "scheduled_task"
            trigger_id="bootstrap_validation",  # Placeholder
            metadata=trigger_config.parameters or {}
        )
    
    def _validate_dto_dependencies(
        self,
        blueprint: StrategyBlueprint,
        errors: List[str],
        warnings: List[str]
    ):
        """Validate that all required DTOs have producers."""
        
        # Build map: DTO type → workers that produce it
        producers: dict[str, list[str]] = {}
        for worker_config in blueprint.workforce.all_workers():
            manifest = self._plugins.get_manifest(worker_config.plugin)
            for dto_name in manifest.produces_dtos:
                producers.setdefault(dto_name, []).append(worker_config.plugin)
        
        # Check each worker's requirements
        for worker_config in blueprint.workforce.all_workers():
            manifest = self._plugins.get_manifest(worker_config.plugin)
            
            # Check CRITICAL DTOs
            critical = manifest.requires_system_resources.context_dtos.critical
            for dto_name in critical:
                if dto_name not in producers:
                    errors.append(
                        f"Worker '{worker_config.plugin}' requires CRITICAL DTO "
                        f"'{dto_name}' but no worker in workforce produces it. "
                        f"Add a producer or remove this worker."
                    )
            
            # Optional DTOs just get warnings
            optional = manifest.requires_system_resources.context_dtos.get("optional", [])
            for dto_name in optional:
                if dto_name not in producers:
                    warnings.append(
                        f"Worker '{worker_config.plugin}' has OPTIONAL dependency "
                        f"on '{dto_name}' which is not produced. "
                        f"Worker will run with degraded accuracy."
                    )
```

**Example Bootstrap Validation:**

```python
# operation.yaml defines triggers
triggers:
  - type: "market_tick"
    exchange: "kraken"
    symbols: ["BTC/USD"]
  
  - type: "scheduled_task"
    schedule: "0 8 * * MON"  # Weekly DCA

# Validation checks:
# 1. Does momentum_signal work with market_tick? 
#    → Check if "realtime_price" in market_tick capabilities ✅
# 2. Does momentum_signal work with scheduled_task?
#    → Check if "realtime_price" in scheduled_task capabilities ❌
#    → ERROR: Remove worker OR remove scheduled_task trigger
```

---

## 3. Fail-Fast at Runtime

### 3.1 ITradingContextProvider - NO Optionals!

```python
# backend/core/interfaces/trading_context_provider.py

@runtime_checkable
class ITradingContextProvider(Protocol):
    """
    Context provider with GUARANTEED contracts.
    
    If bootstrap validation passed, runtime NEVER returns None.
    All failures are EXCEPTIONS (fail-fast).
    
    Worker-agnostic: NO flow type knowledge needed!
    """
    
    def start_new_tick(
        self,
        tick_cache: TickCacheType,
        timestamp: datetime,
        asset: str,
        trigger_context: TriggerContext,  # Platform concept, NOT exposed to workers
        **capabilities_data  # Data for each available capability
    ) -> None:
        """
        Configure provider for new strategy run.
        
        Args:
            tick_cache: Multi-asset cache
            timestamp: Run trigger timestamp
            asset: Asset identifier
            trigger_context: What triggered this run (platform-level, for journaling)
            **capabilities_data: Capability-specific data provided by platform
                Examples based on available capabilities:
                - realtime_price: Decimal
                - tick_volume: Decimal
                - news_headline: str
                - schedule_task_name: str
        
        Raises:
            FlowConfigurationError: If required capability data missing
        """
        ...
    
    def get_base_context(self, asset: str | None = None) -> BaseContextDTO:
        """
        Get base context - GUARANTEED to have all data.
        
        Returns:
            BaseContextDTO with ALL fields populated (no Nones!)
        
        Raises:
            NoActiveFlowError: If no run active
            AssetNotInCacheError: If asset not initialized
        """
        ...
    
    def get_required_dtos(
        self,
        requesting_worker: IWorker,
        dto_types: list[Type[BaseModel]] | None = None,
        asset: str | None = None
    ) -> Dict[Type[BaseModel], BaseModel]:
        """
        Get required DTOs - GUARANTEED to return all critical deps.
        
        Returns:
            Dict with ALL requested DTOs (no missing entries!)
        
        Raises:
            MissingCriticalDependencyError: If critical DTO not in cache
                (This should NEVER happen if bootstrap validation passed!)
        """
        ...
```

### 3.2 BaseContextDTO - Capability-Driven

```python
# backend/dtos/shared/base_context.py

from pydantic import BaseModel, Field
from datetime import datetime
from decimal import Decimal

class BaseContextDTO(BaseModel):
    """
    Base context - contains data from ALL available capabilities.
    
    Fields are populated based on what capabilities were available
    when run was triggered. Bootstrap validation ensures workers
    ONLY run when their required capabilities are present.
    
    NO flow type discrimination! Just capability data.
    """
    
    # === UNIVERSAL FIELDS (always present) ===
    asset: str = Field(...)
    timestamp: datetime = Field(...)
    
    # === CAPABILITY FIELDS (present if capability available) ===
    # Capability: "realtime_price"
    current_price: Decimal | None = Field(None, gt=0)
    
    # Capability: "tick_volume"
    volume: Decimal | None = Field(None, ge=0)
    
    # Capability: "tick_spread"
    spread: Decimal | None = Field(None, ge=0)
    
    # Capability: "news_metadata"
    news_headline: str | None = Field(None)
    news_sentiment: str | None = Field(None)
    
    # Capability: "schedule_metadata"
    schedule_task_name: str | None = Field(None)
    schedule_params: dict | None = Field(None)
    
    class Config:
        frozen = True
    
    def has_capability_data(self, capability: str) -> bool:
        """
        Check if data for given capability is present.
        
        Workers SHOULD NOT use this for critical capabilities
        (those are guaranteed by bootstrap validation).
        Only use for optional capabilities.
        """
        capability_field_map = {
            "realtime_price": "current_price",
            "tick_volume": "volume",
            "tick_spread": "spread",
            "news_metadata": "news_headline",
            "schedule_metadata": "schedule_task_name",
        }
        
        field_name = capability_field_map.get(capability)
        if not field_name:
            return False
        
        return getattr(self, field_name) is not None
```

**Key Design Shift:**
- BaseContextDTO has **optional fields** (capability data may or may not be present)
- Workers **never check** these fields directly (bootstrap guarantees requirements)
- Workers just **use** the data (e.g., `ctx.current_price`) - guaranteed non-None for their capabilities

**Key Benefits:**
- Worker code has **zero platform awareness**
- Same worker can run in different trigger contexts (as long as capabilities met)
- Testing is simple: mock BaseContextDTO with required fields populated
- No flow type enums, no isinstance checks

---

## 4. Failure Scenarios & Fail-Fast Behavior (Simplified)

### 4.1 Scenario 1: Worker Needs Capability Not Available for Trigger

**Configuration:**
```yaml
# strategy_blueprint.yaml
workforce:
  opportunity_workers:
    - plugin: "momentum_signal"  
      # Manifest requires: ["realtime_price", "ohlcv_window"]

# operation.yaml  
triggers:
  - type: "scheduled_task"
    schedule: "0 8 * * MON"  # Weekly DCA
    # ❌ scheduled_task doesn't provide "realtime_price" capability!
```

**Fail-Fast Point: BOOTSTRAP**
```python
# During OperationService.bootstrap()
validator = DependencyValidator(plugin_registry, capability_registry)

# Build trigger context for scheduled_task
trigger_ctx = TriggerContext(
    trigger_type="scheduled_task",
    trigger_id="bootstrap_validation",
    metadata={"schedule": "0 8 * * MON"}
)

# Check available capabilities for this trigger
available_caps = capability_registry.get_available_capabilities(trigger_ctx)
# Returns: {"ohlcv_window", "ledger_state", "schedule_metadata"}
# NOT "realtime_price"!

# Validate worker requirements
manifest = plugin_registry.get_manifest("momentum_signal")
required = manifest.requires_system_resources.capabilities
# ["realtime_price", "ohlcv_window"]

missing = [cap for cap in required if cap not in available_caps]
# ["realtime_price"]

# ❌ FAILS IMMEDIATELY
raise ConfigurationError(
    "Worker 'momentum_signal' requires capabilities ['realtime_price'] "
    "which are NOT available for trigger 'scheduled_task'. "
    "Available: ['ledger_state', 'ohlcv_window', 'schedule_metadata']. "
    "Either remove worker or remove this trigger from operation config."
)
```

**Impact on TickCache/Provider:** NONE - Never gets created!

---

### 4.2 Scenario 2: Missing DTO Producer

**Configuration:**
```yaml
workforce:
  opportunity_workers:
    - plugin: "fvg_detector"  # Requires: MarketStructureDTO (critical!)
  
  # ❌ NO market_structure_detector in context_workers!
```

**Fail-Fast Point: BOOTSTRAP**
```python
validator.validate_strategy(blueprint, flow_types)

# ❌ FAILS:
# "Worker 'fvg_detector' requires CRITICAL DTO 'MarketStructureDTO'
#  but no worker in workforce produces it.
#  Add 'market_structure_detector' to context_workers."
```

**Impact on TickCache/Provider:** NONE - Bootstrap fails before runtime!

---

### 4.3 Scenario 3: Capability Provider Unavailable

**Configuration:**
```yaml
# Worker manifest
requires_system_resources:
  capabilities:
    - "market_depth"  # Needs orderbook data

# ExecutionEnvironment
connector: "kraken_rest_api"  # ❌ NO market depth support (only websocket has it)
```

**Fail-Fast Point: BOOTSTRAP**
```python
# During OperationService.bootstrap()

# Check if capability provider is registered
if not capability_registry.supports_capability("market_depth"):
    raise ConfigurationError(
        "Worker 'orderbook_imbalance_detector' requires capability 'market_depth' "
        "which is NOT registered in platform. "
        "Available capabilities: ['realtime_price', 'ohlcv_window', 'ledger_state']. "
        "Either remove worker or add market_depth provider."
    )

# Even if registered, check if connector supports it
connector_caps = connector.get_supported_capabilities()
# kraken_rest_api returns: ["ohlcv_window"] (NO market_depth!)

if "market_depth" not in connector_caps:
    raise ConfigurationError(
        "Worker 'orderbook_imbalance_detector' requires capability 'market_depth' "
        "which is NOT supported by connector 'kraken_rest_api'. "
        "Available from connector: ['ohlcv_window']. "
        "Either switch to 'kraken_websocket' connector or remove worker."
    )
```

**Impact on TickCache/Provider:** NONE!

---

### 4.4 Scenario 4: Runtime DTO Missing (SHOULD NEVER HAPPEN!)

**Situation:** Critical DTO not in cache during runtime

**This indicates a BUG in:**
- Bootstrap validation (didn't catch missing producer)
- Wiring (producer never executed)
- Worker (failed to produce promised DTO)

**Fail-Fast Behavior:**
```python
class TradingContextProvider:
    def get_required_dtos(
        self,
        requesting_worker: IWorker,
        dto_types: list[Type[BaseModel]] | None = None,
        asset: str | None = None
    ) -> Dict[Type[BaseModel], BaseModel]:
        """Get DTOs - fails fast if critical deps missing."""
        
        # Determine critical vs optional from manifest
        manifest = self._get_worker_manifest(requesting_worker)
        critical_dtos = {
            req.name for req in manifest.requires_context_dtos.critical
        }
        
        # Fetch from cache
        result = {}
        missing_critical = []
        
        for dto_type in (dto_types or manifest.all_required_dto_types):
            dto_name = dto_type.__name__
            
            if dto_type in self._current_tick_cache[asset]:
                result[dto_type] = self._current_tick_cache[asset][dto_type]
            elif dto_name in critical_dtos:
                # ❌ CRITICAL DTO MISSING - FAIL FAST!
                missing_critical.append(dto_name)
            else:
                # Optional DTO missing - just log warning
                self._logger.warning(
                    f"Optional DTO '{dto_name}' not in cache for "
                    f"worker '{requesting_worker.__class__.__name__}'. "
                    f"Proceeding with degraded accuracy."
                )
        
        if missing_critical:
            # ❌ FAIL IMMEDIATELY - DO NOT CONTINUE!
            raise MissingCriticalDependencyError(
                f"Worker '{requesting_worker.__class__.__name__}' requires "
                f"CRITICAL DTOs {missing_critical} which are NOT in cache! "
                f"This indicates a bootstrap validation bug or wiring failure. "
                f"HALTING FLOW to prevent corrupt trading decisions.",
                missing_dtos=missing_critical,
                worker=requesting_worker.__class__.__name__,
                asset=asset
            )
        
        return result
```

**Impact on TickCache:**
- TickCache content is NOT changed (no fallback/default values)
- Flow is **HALTED immediately**
- Exception propagates up → EventAdapter → TickCacheManager
- TickCacheManager publishes `FLOW_FAILED` event
- Strategy run aborts (no partial execution)

**Journaling:**
```python
# In exception handler
self._journal.log_critical_error(
    event_type="MISSING_CRITICAL_DEPENDENCY",
    worker=requesting_worker.__class__.__name__,
    missing_dtos=missing_critical,
    causality=current_causality_chain,
    message="Flow halted due to missing critical dependency - likely config/wiring bug"
)
```

---

### 4.5 Scenario 5: Connection Loss During Flow (External Failure)

**Situation:** Platform provider fails mid-flow (e.g., market data feed drops)

```python
class OhlcvProvider:
    def get_window(self, end_time: datetime, lookback: int) -> pd.DataFrame:
        """Get OHLCV window - fails fast on connection loss."""
        
        try:
            df = self._fetch_from_exchange(end_time, lookback)
        except ConnectionError as e:
            # ❌ FAIL FAST - DO NOT return partial/stale data!
            raise DataProviderUnavailableError(
                f"OHLCV data unavailable - connection to exchange lost. "
                f"HALTING flow to prevent trading on incomplete data.",
                provider="OhlcvProvider",
                exchange=self._exchange_name,
                original_error=e
            ) from e
        
        return df
```

**Propagation:**
```
Worker.process()
  → ohlcv_provider.get_window()
    → ❌ DataProviderUnavailableError
  → Worker propagates exception
  → EventAdapter catches
  → Publishes FLOW_FAILED event
  → TickCacheManager cleans up cache
  → Strategy run aborted
```

**Impact on TickCache:**
- Cache is **cleared** (via TickCacheManager.clear_cache())
- NO partial results persisted
- Next flow starts with fresh cache

**Recovery:**
```python
# In OperationService main loop
while operation_active:
    try:
        # Wait for trigger event (tick/news/schedule)
        event = await event_bus.wait_for_trigger()
        
        # Start flow
        tick_cache_manager.handle_trigger_event(event)
        
    except DataProviderUnavailableError as e:
        # Log failure
        logger.error(f"Flow failed due to data unavailability: {e}")
        journal.log_flow_failure(event, error=e)
        
        # ⚠️ Graceful degradation: Skip this flow, continue operation
        # Alternative: Pause strategy until connection restored
        
        continue  # Try next flow
```

---

## 5. ITradingContextProvider Interface - Final Design (Simplified)

### 5.1 Method Signatures (Fail-Fast, Capability-Driven)

```python
@runtime_checkable
class ITradingContextProvider(Protocol):
    """
    Context provider with fail-fast guarantees.
    
    Design Principles:
    - Capability-driven (NO flow type awareness)
    - NO optional returns (Nones mean failure → exception)
    - NO degraded modes (either works or fails)
    - ALL failures are explicit exceptions
    - Bootstrap validation ensures runtime safety
    """
    
    def start_new_tick(
        self,
        tick_cache: TickCacheType,
        timestamp: datetime,
        asset: str,
        trigger_context: TriggerContext,  # For journaling only, NOT worker-visible
        **capability_data  # Data keyed by capability name
    ) -> None:
        """
        Initialize provider for new strategy run.
        
        Args:
            tick_cache: Multi-asset cache
            timestamp: Run trigger timestamp
            asset: Asset identifier
            trigger_context: Platform-level trigger info (for journaling)
            **capability_data: Capability-specific data
                Example for market_tick trigger:
                    realtime_price=Decimal("50000.00"),
                    tick_volume=Decimal("1.5"),
                    tick_spread=Decimal("0.50")
                Example for news_event trigger:
                    news_headline="Fed raises rates",
                    news_sentiment="bearish"
        
        Raises:
            FlowConfigurationError: Required capability data missing
        """
        ...
    
    def get_base_context(
        self,
        asset: str | None = None
    ) -> BaseContextDTO:
        """
        Get base context - fields populated based on available capabilities.
        
        Workers NEVER check optional fields - bootstrap guarantees
        their required capabilities are present.
        
        Returns:
            BaseContextDTO with capability data populated
        
        Raises:
            NoActiveFlowError: No run initialized
            AssetNotInCacheError: Asset not initialized in run
        """
        ...
    
    def get_required_dtos(
        self,
        requesting_worker: IWorker,
        dto_types: list[Type[BaseModel]] | None = None,
        asset: str | None = None
    ) -> Dict[Type[BaseModel], BaseModel]:
        """
        Get DTOs - ALL critical deps guaranteed present.
        
        Returns:
            Dict with ALL critical DTOs (optional may be missing)
        
        Raises:
            MissingCriticalDependencyError: Critical DTO not in cache
                → Indicates bootstrap bug or wiring failure
                → Run MUST be halted
        """
        ...
    
    def set_result_dto(
        self,
        producing_worker: IWorker,
        result_dto: BaseModel,
        asset: str | None = None
    ) -> None:
        """
        Store result DTO - validates against manifest.
        
        Raises:
            UnexpectedDTOTypeError: DTO type not in manifest.produces_dtos
                → Indicates worker implementation bug
            NoActiveFlowError: No run active
        """
        ...
    
    def has_dto(
        self,
        dto_type: Type[BaseModel],
        asset: str | None = None
    ) -> bool:
        """
        Check DTO presence - for OPTIONAL dependencies only!
        
        Workers should NOT use this for critical deps
        (those are guaranteed by bootstrap validation).
        
        Returns:
            True if DTO in cache, False otherwise
        """
        ...
    
    def clear_cache(self) -> None:
        """
        Clear cache - called after run completion OR failure.
        
        No exceptions - always succeeds (even if cache empty).
        """
        ...
```

### 5.2 Exception Hierarchy

```python
# backend/core/exceptions.py

class ContextProviderError(Exception):
    """Base for all provider errors."""
    pass

# === BOOTSTRAP-TIME ERRORS (should never reach runtime) ===
class ConfigurationError(ContextProviderError):
    """Strategy configuration invalid - caught at bootstrap."""
    pass

# === RUNTIME ERRORS (fail-fast) ===
class NoActiveFlowError(ContextProviderError):
    """No flow initialized - worker called before start_new_tick()."""
    pass

class AssetNotInCacheError(ContextProviderError):
    """Requested asset not initialized in current flow."""
    def __init__(self, asset: str, available_assets: list[str]):
        self.asset = asset
        self.available_assets = available_assets
        super().__init__(
            f"Asset '{asset}' not in cache. Available: {available_assets}"
        )

class MissingCriticalDependencyError(ContextProviderError):
    """
    Critical DTO missing from cache.
    
    This should NEVER happen if bootstrap validation passed!
    Indicates:
    - Bootstrap validation bug
    - Wiring configuration error
    - Producer worker failed to produce promised DTO
    
    Flow MUST be halted - DO NOT continue with incomplete data!
    """
    def __init__(self, message: str, missing_dtos: list[str], worker: str, asset: str):
        self.missing_dtos = missing_dtos
        self.worker = worker
        self.asset = asset
        super().__init__(message)

class UnexpectedDTOTypeError(ContextProviderError):
    """Worker produced DTO not declared in manifest.produces_dtos."""
    pass

class FlowConfigurationError(ContextProviderError):
    """Flow started with invalid/missing required data."""
    pass

# === EXTERNAL FAILURES (infrastructure) ===
class DataProviderUnavailableError(ContextProviderError):
    """Platform provider failed (connection loss, timeout, etc.)."""
    def __init__(self, message: str, provider: str, original_error: Exception):
        self.provider = provider
        self.original_error = original_error
        super().__init__(message)
```

---

## 6. Strategy Builder UI Integration (Simplified)

### 6.1 Real-Time Validation (Capability-Driven)

```typescript
// frontends/web/src/components/StrategyBuilder.tsx

interface WorkerPlacementValidation {
  canPlace: boolean;
  errors: string[];
  warnings: string[];
}

function validateWorkerPlacement(
  worker: PluginManifest,
  currentWorkforce: WorkerConfig[],
  triggerConfigs: TriggerConfig[]  // From operation config
): WorkerPlacementValidation {
  const errors: string[] = [];
  const warnings: string[] = [];
  
  // 1. Check capability availability for EACH trigger
  for (const trigger of triggerConfigs) {
    const triggerCtx = buildTriggerContext(trigger);
    const availableCaps = capabilityRegistry.getAvailableCapabilities(triggerCtx);
    
    const requiredCaps = worker.requires_system_resources.capabilities;
    const missingCaps = requiredCaps.filter(cap => !availableCaps.has(cap));
    
    if (missingCaps.length > 0) {
      errors.push(
        `For trigger '${trigger.type}', worker needs: ${missingCaps.join(', ')} ` +
        `which are NOT available. Available: ${Array.from(availableCaps).join(', ')}. ` +
        `Remove worker or remove this trigger.`
      );
    }
  }
  
  // 2. Check DTO dependencies
  const criticalDtos = worker.requires_system_resources.context_dtos.critical;
  const availableProducers = getAvailableProducers(currentWorkforce);
  
  for (const dtoName of criticalDtos) {
    if (!availableProducers.has(dtoName)) {
      errors.push(
        `Worker requires CRITICAL DTO '${dtoName}' but no producer in workforce. ` +
        `Add a producer worker first.`
      );
    }
  }
  
  // 3. Check optional dependencies (warnings only)
  const optionalDtos = worker.requires_system_resources.context_dtos.optional || [];
  for (const dtoName of optionalDtos) {
    if (!availableProducers.has(dtoName)) {
      warnings.push(
        `Optional DTO '${dtoName}' not produced - worker will run with reduced accuracy`
      );
    }
  }
  
  return {
    canPlace: errors.length === 0,
    errors,
    warnings
  };
}
```

**Key Difference:**
- NO flow type dropdown/selection in UI
- Validation checks capability availability per trigger
- Same validation logic as DependencyValidator (capability-based)

### 6.2 Visual Feedback

```typescript
// UI shows validation state in real-time

<WorkerCard 
  worker={momentumSignal}
  validation={validateWorkerPlacement(momentumSignal, workforce, ["scheduled_task"])}
>
  {validation.canPlace ? (
    <Badge color="green">✓ Compatible</Badge>
  ) : (
    <>
      <Badge color="red">✗ Incompatible</Badge>
      <ErrorList>
        {validation.errors.map(err => (
          <ErrorItem key={err}>
            <Icon name="alert-circle" />
            {err}
          </ErrorItem>
        ))}
      </ErrorList>
    </>
  )}
</WorkerCard>
```

---

## 7. Decision Summary (REVISED - Capability-Driven)

### ✅ FINAL DECISIONS:

**#4: BaseContextDTO Design**
- **Single unified BaseContextDTO** with optional capability fields
- Fields populated based on available capabilities (not flow types)
- **NO flow type discrimination** in worker code
- Workers declare required capabilities, platform guarantees them

**#5: Fail-Fast Policy**
- **Bootstrap validation** catches 99% of errors (capability mismatches, missing deps, unavailable providers)
- **Runtime exceptions** for the 1% (infrastructure failures, bugs)
- **NO graceful degradation** in provider (fail immediately, halt run)
- **NO partial data** in cache (all-or-nothing per run)

**#6: Validation Timing**
- **Bootstrap (DependencyValidator)**: Capability availability per trigger, DTO dependency chains
- **Runtime (Provider)**: Sanity checks, type validation, critical dependency enforcement
- **UI (Strategy Builder)**: Real-time validation per trigger, visual feedback, same logic as DependencyValidator

### Impact on ITradingContextProvider:

| Aspect | Design Decision |
|--------|----------------|
| **Flow Type Awareness** | NONE - capability-driven only |
| **Optional Parameters** | NONE - all failures are exceptions |
| **Optional Returns** | NONE - methods never return None for guaranteed data |
| **Degradation Logic** | NONE - fail-fast, no fallbacks |
| **Cache Content** | Clean - no default/placeholder values |
| **Error Handling** | Explicit exceptions, clear failure modes |
| **Thread Safety** | Simple - no complex fallback coordination |
| **Testing** | Easy - happy path only (failures caught at bootstrap) |
| **Worker Code** | Platform-agnostic - just uses required capabilities |

### Key Architectural Shift:

**BEFORE (Flow Type Approach):**
```yaml
# Worker declares flow compatibility
compatible_flow_types: ["market_tick"]
```
→ Worker is **coupled to platform concepts** (flow types)
→ Multi-interpretable: What IS a flow type exactly?

**AFTER (Capability Approach):**
```yaml
# Worker declares resource needs
requires_system_resources:
  capabilities: ["realtime_price", "ohlcv_window"]
```
→ Worker is **decoupled from platform** (just declares needs)
→ Unambiguous: Capabilities are concrete, well-defined resources
→ Platform decides: "Can I provide these for THIS trigger?"

---

**Document Owner:** Architecture Team  
**Status:** ✅ Design Complete - SIMPLIFIED to Capability-Driven Model  
**Last Updated:** 2025-10-28
