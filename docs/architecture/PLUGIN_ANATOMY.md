# Plugin Anatomy

**Status:** Architecture Foundation  
**Last Updated:** 2025-10-29

---

## Overview

Plugins are self-contained Python packages that encapsulate strategy logic. Each plugin defines a worker, its configuration schema, dependencies, and capabilities. The platform loads and wires plugins based on YAML configuration.

**Key Principles:**
- **Self-Contained**: Each plugin is an independent Python package
- **Manifest-Driven**: All metadata declared in `manifest.yaml`
- **Contract-Based**: Dependencies via DTOs, capabilities via platform injection
- **Testable**: Mandatory unit tests for all plugins

---

## Folder Structure

### Basic Plugin Structure

```
plugins/[category]/[plugin_name]/
├── manifest.yaml           # Plugin ID card + capability declarations
├── worker.py               # Business logic implementation
├── schema.py               # Pydantic configuration model
├── context_schema.py       # Visualization contract (optional)
├── dtos/                   # Plugin-specific DTOs (optional)
│   ├── __init__.py
│   └── my_output_dto.py
└── test/
    └── test_worker.py      # Mandatory unit tests
```

### When to Include `dtos/` Folder

**Include `dtos/` folder ONLY if:**
- Plugin produces DTOs for TickCache (context enrichment, intermediate data)
- DTOs need to be consumed by other workers

**Do NOT include `dtos/` folder if:**
- Plugin only publishes system DTOs (OpportunitySignal, ThreatSignal, StrategyDirective)
- Plugin is pure consumer (only reads from TickCache)

**Note:** ~95% of plugins do NOT have a `dtos/` folder.

### Category Organization

Plugins are organized by worker category:

```
plugins/
├── context_workers/        # ContextWorker plugins
│   ├── ema_detector/
│   ├── regime_classifier/
│   └── support_resistance/
├── opportunity_workers/    # OpportunityWorker plugins
│   ├── breakout_scout/
│   ├── momentum_signal/
│   └── mean_reversion/
├── threat_workers/         # ThreatWorker plugins
│   ├── drawdown_monitor/
│   └── volatility_spike/
├── planning_workers/       # PlanningWorker plugins
│   ├── limit_entry_planner/
│   ├── kelly_sizer/
│   └── trailing_stop_planner/
└── strategy_planners/      # StrategyPlanner plugins
    ├── swot_momentum/
    ├── trailing_manager/
    └── dca_scheduler/
```

---

## manifest.yaml Structure

### Complete Example

```yaml
identification:
  name: "ema_detector"
  display_name: "EMA Detector"
  type: "context_worker"  # Worker category
  subtype: "indicator_calculation"  # See taxonomy
  version: "1.0.0"
  description: "Calculates exponential moving averages"
  author: "Strategy Team"

dependencies:
  # DTOs required from other workers
  requires_dtos:
    - source: "backend.dto_reg.s1mple.regime_classifier.v1_0_0.regime_output_dto"
      dto_class: "RegimeOutputDTO"
  
  # DTOs produced by this worker
  produces_dtos:
    - dto_class: "EMAOutputDTO"
      local_path: "dtos/ema_output_dto.py"

capabilities:
  # Standard capability (ALWAYS present, NOT configurable)
  context_access:
    enabled: true  # IStrategyCache
  
  # Opt-in capabilities
  ohlcv_window:
    enabled: true  # IOhlcvProvider - Historical OHLCV data
  
  state_persistence:
    enabled: true  # IStateProvider - Worker state storage
    scope: "strategy"  # OR "global"
  
  journaling:
    enabled: true  # IJournalWriter - Audit trail logging
```

### Identification Section

```yaml
identification:
  name: "my_worker"            # Unique identifier (snake_case)
  display_name: "My Worker"   # Human-readable name
  type: "context_worker"       # Worker category (see taxonomy)
  subtype: "indicator_calculation"  # Worker subtype
  version: "1.0.0"             # Semantic versioning
  description: "Short description of functionality"
  author: "Developer Name"
```

**Valid Worker Types:**
- `context_worker`
- `opportunity_worker`
- `threat_worker`
- `planning_worker`
- `strategy_planner`

**Subtypes:** See [Worker Taxonomy](WORKER_TAXONOMY.md) for valid subtypes per category.

---

### Dependencies Section

#### Deprecated: DataFrame Column Dependencies (V2)
```yaml
# OLD APPROACH (DEPRECATED)
dependencies:
  requires: ['close', 'volume']  # DataFrame columns
  provides: ['ema_20']           # DataFrame columns
```

#### Current: Point-in-Time DTO Dependencies (V3)

```yaml
dependencies:
  # DTOs required from other workers
  requires_dtos:
    - source: "backend.dto_reg.vendor.plugin.version.dto_module"
      dto_class: "InputDTO"
    - source: "backend.dto_reg.s1mple.ema_detector.v1_0_0.ema_output_dto"
      dto_class: "EMAOutputDTO"
  
  # DTOs produced by this worker
  produces_dtos:
    - dto_class: "MyOutputDTO"
      local_path: "dtos/my_output_dto.py"
    - dto_class: "AlternativeOutputDTO"
      local_path: "dtos/alternative_output_dto.py"
```

**Notes:**
- `requires_dtos`: DTOs this worker consumes from TickCache
- `produces_dtos`: DTOs this worker stores to TickCache
- `source`: Fully qualified path in `dto_reg` (enrolled location)
- `local_path`: Relative path within plugin folder

---

### Capabilities Section

```yaml
capabilities:
  # Standard capability (ALWAYS available)
  context_access:
    enabled: true  # IStrategyCache - REQUIRED, NOT configurable
  
  # Historical data capabilities
  ohlcv_window:
    enabled: true  # IOhlcvProvider - OHLCV bars
  
  multi_timeframe:
    enabled: true  # IMtfProvider - Multiple timeframes
  
  # State & persistence
  state_persistence:
    enabled: true  # IStateProvider - Worker state
    scope: "strategy"  # "strategy" OR "global"
  
  # Market data
  market_depth:
    enabled: true  # IDepthProvider - Order book
  
  # Portfolio & execution
  ledger_state:
    enabled: true  # ILedgerProvider - Positions/portfolio
  
  # Logging
  journaling:
    enabled: true  # IJournalWriter - Audit trail
  
  # Event-driven (for EventDrivenWorker)
  events:
    enabled: true
    publishes:
      - event_name: "MY_CUSTOM_EVENT"
        description: "Event description"
    wirings:
      - listens_to: "TRIGGER_EVENT"
        invokes:
          method: "on_trigger"
          requires_payload: true
```

**Capability Injection:**
- WorkerFactory reads manifest
- Validates capability contracts
- Injects requested providers at instantiation
- Workers access via `self.provider_name`

---

## Worker Implementation Patterns

### 1. StandardWorker (90% of Plugins)

**Use for:** Synchronous, single-method processing (context, opportunity detection, planning)

```python
# plugins/context_workers/ema_detector/worker.py
from backend.core.base_worker import StandardWorker
from backend.shared_dtos.disposition_envelope import DispositionEnvelope
from .dtos.ema_output_dto import EMAOutputDTO

class EMADetector(StandardWorker):
    """Calculates exponential moving averages and stores to TickCache."""
    
    def process(self) -> DispositionEnvelope:
        # 1. Get run anchor (timestamp validation)
        run_anchor = self.strategy_cache.get_run_anchor()
        
        # 2. Get platform data
        df = self.ohlcv_provider.get_window(run_anchor.timestamp, lookback=100)
        
        # 3. Calculate
        ema_20 = df['close'].ewm(span=20).mean().iloc[-1]
        ema_50 = df['close'].ewm(span=50).mean().iloc[-1]
        
        # 4. Store to TickCache
        output_dto = EMAOutputDTO(
            ema_20=ema_20,
            ema_50=ema_50,
            timestamp=run_anchor.timestamp
        )
        self.strategy_cache.set_result_dto(self, output_dto)
        
        # 5. Signal continuation
        return DispositionEnvelope(disposition="CONTINUE")
```

**Key Methods:**
- `process() -> DispositionEnvelope` - Main processing method (REQUIRED)

**Injected Providers** (based on manifest capabilities):
- `self.strategy_cache` - IStrategyCache (always available)
- `self.ohlcv_provider` - IOhlcvProvider (if `ohlcv_window` enabled)
- `self.state_provider` - IStateProvider (if `state_persistence` enabled)
- `self.journal_writer` - IJournalWriter (if `journaling` enabled)

---

### 2. EventDrivenWorker (Complex Workflows)

**Use for:** Asynchronous, event-triggered processing (scheduled operations, multi-event logic)

```python
# plugins/strategy_planners/dca_scheduler/worker.py
from backend.core.base_worker import EventDrivenWorker
from backend.shared_dtos.disposition_envelope import DispositionEnvelope
from backend.dtos.strategy.strategy_directive import StrategyDirective

class DCAScheduler(EventDrivenWorker):
    """Executes dollar-cost averaging on schedule."""
    
    # Event handler (method name from manifest.wirings)
    def on_weekly_tick(self, payload: dict) -> DispositionEnvelope:
        # 1. Check conditions
        portfolio = self.ledger_provider.get_current_state()
        
        # 2. Build directive
        if portfolio.cash_available > 100:
            directive = StrategyDirective(
                scope="NEW_TRADE",
                sub_directives=[...],
                causality=self._build_causality()
            )
            
            # 3. Publish decision
            return DispositionEnvelope(
                disposition="PUBLISH",
                event_name="STRATEGY_DIRECTIVE_READY",
                event_payload=directive
            )
        
        # 4. No action - stop flow
        return DispositionEnvelope(disposition="STOP")
```

**Key Features:**
- Multiple event handlers (one per `manifest.wirings` entry)
- Handler method names defined in manifest
- Can access event payload via method parameter

**Manifest Configuration:**
```yaml
capabilities:
  events:
    enabled: true
    wirings:
      - listens_to: "WEEKLY_SCHEDULE_TICK"
        invokes:
          method: "on_weekly_tick"
          requires_payload: true
```

---

## Configuration Schema (schema.py)

### Purpose
Define plugin-specific configuration parameters (e.g., indicator periods, thresholds)

### Example
```python
# plugins/context_workers/ema_detector/schema.py
from pydantic import BaseModel, Field

class EMADetectorConfig(BaseModel):
    """Configuration for EMA Detector worker."""
    
    fast_period: int = Field(
        default=20,
        ge=5,
        le=100,
        description="Fast EMA period"
    )
    
    slow_period: int = Field(
        default=50,
        ge=10,
        le=200,
        description="Slow EMA period"
    )
    
    lookback_bars: int = Field(
        default=100,
        ge=50,
        le=500,
        description="Historical bars required"
    )
```

### Usage in Worker
```python
class EMADetector(StandardWorker):
    config: EMADetectorConfig  # Injected by WorkerFactory
    
    def process(self) -> DispositionEnvelope:
        df = self.ohlcv_provider.get_window(
            timestamp, 
            lookback=self.config.lookback_bars
        )
        ema_fast = df['close'].ewm(span=self.config.fast_period).mean()
        ...
```

---

## Plugin-Specific DTOs (Optional)

### When to Create

Create `dtos/` folder and DTOs when:
- Worker produces intermediate data for downstream workers
- Data structure is plugin-specific (not a system DTO)
- Other workers need to consume this data

### Example DTO

```python
# plugins/context_workers/ema_detector/dtos/ema_output_dto.py
from pydantic import BaseModel, Field
from datetime import datetime

class EMAOutputDTO(BaseModel):
    """EMA indicator output for TickCache."""
    
    ema_20: float = Field(..., description="20-period EMA")
    ema_50: float = Field(..., description="50-period EMA")
    ema_200: float | None = Field(None, description="200-period EMA (optional)")
    
    timestamp: datetime = Field(..., description="Calculation timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ema_20": 45234.56,
                "ema_50": 45100.23,
                "ema_200": 44500.00,
                "timestamp": "2025-10-29T10:30:00Z"
            }
        }
```

### DTO Enrollment Process

1. **Definition**: Create DTO in `plugins/[category]/[plugin]/dtos/`
2. **Manifest**: Declare in `produces_dtos` section
3. **Enrollment**: Platform copies to `backend/dto_reg/[vendor]/[plugin]/[version]/`
4. **Consumption**: Other plugins import from `backend.dto_reg.*`

See [Data Flow](DATA_FLOW.md#dto-sharing-via-enrollment) for detailed enrollment process.

---

## Testing Requirements

### Mandatory Unit Tests

Every plugin MUST include unit tests in `test/test_worker.py`:

```python
# plugins/context_workers/ema_detector/test/test_worker.py
import pytest
from unittest.mock import Mock
from ..worker import EMADetector
from ..schema import EMADetectorConfig
from ..dtos.ema_output_dto import EMAOutputDTO

def test_ema_calculation():
    # Arrange
    worker = EMADetector()
    worker.config = EMADetectorConfig(fast_period=20, slow_period=50)
    worker.strategy_cache = Mock()
    worker.ohlcv_provider = Mock()
    
    # Mock data
    worker.ohlcv_provider.get_window.return_value = create_test_df()
    
    # Act
    result = worker.process()
    
    # Assert
    assert result.disposition == "CONTINUE"
    worker.strategy_cache.set_result_dto.assert_called_once()
    dto = worker.strategy_cache.set_result_dto.call_args[0][1]
    assert isinstance(dto, EMAOutputDTO)
    assert dto.ema_20 > 0
```

**Test Coverage Requirements:**
- Calculation accuracy
- DTO structure validation
- Capability injection
- Error handling
- Edge cases

---

## Related Documentation

- **[Worker Taxonomy](WORKER_TAXONOMY.md)** - Worker categories and responsibilities
- **[Data Flow](DATA_FLOW.md)** - Communication patterns (TickCache, EventBus)
- **[Configuration Layers](CONFIGURATION_LAYERS.md)** - How plugins are configured
- **[Event-Driven Wiring](EVENT_DRIVEN_WIRING.md)** - How plugins are wired together

---

**Last Updated:** 2025-10-29
