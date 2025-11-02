# Strategy DTO Template

## Overview

Copy-paste template for creating new Strategy DTOs in S1mpleTrader V3. Follow this structure for consistency across all DTOs in `backend/dtos/strategy/`.

## Template Structure

### 1. File Header (REQUIRED)

```python
# backend/dtos/strategy/{your_dto_name}.py
"""
{DTOName} DTO - {One-line description of purpose}.

{Extended description explaining:
- What this DTO represents
- Where it fits in pipeline (Worker output? Planner input?)
- Key responsibilities
- What it does NOT contain (separation of concerns)
}

**Refactored to Lean Spec ({Date}):** (if applicable)
- Removed: {fields} (reason)
- Removed: {fields} (reason)

**What Remains:** {Core responsibility}
- {Field category 1}
- {Field category 2}

**Causality Propagation:** (if applicable)
{Explain whether this DTO has causality field or receives from parent}

@layer: DTOs (Strategy {Worker Type} Output)
@dependencies: [pydantic, backend.utils.id_generators, ...]
"""
```

### 2. Imports (3 Groups with Comments)

```python
# Standard library
import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal, Optional

# Third-party
from pydantic import BaseModel, Field, field_validator

# Project modules
from backend.utils.id_generators import generate_{your_dto}_id
from backend.dtos.causality import CausalityChain  # Only if DTO has causality
```

**Rules:**
- **Group 1:** Standard library (datetime, typing, decimal, re)
- **Group 2:** Third-party (pydantic, pytest)
- **Group 3:** Project modules (backend.utils, backend.dtos)
- Alphabetical within groups
- Blank line between groups

### 3. Class Definition

```python
class YourDTOName(BaseModel):
    """
    {One-line summary}.

    {Brief explanation of what this DTO represents and its role}

    **Key Responsibilities:**
    - {Responsibility 1}
    - {Responsibility 2}

    **NOT Responsible For:**
    - {Not this 1} (→ OtherDTO)
    - {Not this 2} (→ AnotherDTO)

    **Usage Example:**
    ```python
    # {Describe example scenario}
    dto = YourDTOName(
        causality=CausalityChain(tick_id="TCK_20251027_100000_a1b2c3d4"),
        field1="value1",
        field2=Decimal("123.45")
    )
    ```

    **Attributes:**
        causality: Causality tracking from tick/news/schedule (if applicable)
        {dto}_id: Auto-generated unique identifier ({PREFIX}_YYYYMMDD_HHMMSS_hash)
        field1: {Description}
        field2: {Description}
        ...
    """
```

### 4. Field Definitions (Ordered)

```python
    # 1. Causality tracking (FIRST if applicable)
    causality: CausalityChain = Field(
        description="Causality tracking - IDs from birth (tick/news/schedule)"
    )

    # 2. Primary identifier (SECOND)
    {dto}_id: str = Field(
        default_factory=generate_{your_dto}_id,
        pattern=r'^{PREFIX}_\d{8}_\d{6}_[0-9a-f]{8}$',
        description="Unique identifier ({PREFIX}_YYYYMMDD_HHMMSS_hash format)"
    )

    # 3. Timestamp (if applicable)
    timestamp: datetime = Field(
        description="When this {event} occurred (UTC)"
    )

    # 4. Core data fields (alphabetical or logical grouping)
    asset: str = Field(
        min_length=5,
        max_length=20,
        pattern=r'^[A-Z0-9_]+/[A-Z0-9_]+$',
        description="Trading pair (BASE/QUOTE format)"
    )

    direction: Literal["long", "short"] = Field(
        description="Trading direction"
    )

    # 5. Optional fields (LAST)
    confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional confidence score"
    )
```

**Field Order:**
1. `causality` (if DTO tracks causality chain)
2. Primary ID (`{dto}_id`)
3. `timestamp` (if DTO is timestamped)
4. Core data fields (logical grouping)
5. Optional fields (at end)

### 5. Validators (if needed)

```python
    @field_validator('{dto}_id')
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        """Validate {dto}_id follows military datetime format."""
        pattern = r'^{PREFIX}_\d{8}_\d{6}_[0-9a-f]{8}$'
        if not re.match(pattern, v):
            raise ValueError(
                f"{dto}_id must match format {PREFIX}_YYYYMMDD_HHMMSS_hash, got: {v}"
            )
        return v

    @field_validator('timestamp')
    @classmethod
    def ensure_utc_timezone(cls, v: datetime) -> datetime:
        """Ensure timestamp is timezone-aware and in UTC."""
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)

    @field_validator('signal_type')  # Example: UPPER_SNAKE_CASE validation
    @classmethod
    def validate_signal_type_format(cls, v: str) -> str:
        """Validate UPPER_SNAKE_CASE format and reserved prefixes."""
        # Check reserved prefixes
        reserved_prefixes = ['SYSTEM_', 'INTERNAL_', '_']
        if any(v.startswith(prefix) for prefix in reserved_prefixes):
            raise ValueError(
                f"signal_type cannot start with reserved prefix: {v}"
            )

        # Check UPPER_SNAKE_CASE pattern
        pattern = r'^[A-Z][A-Z0-9_]*$'
        if not re.match(pattern, v):
            raise ValueError(
                f"signal_type must follow UPPER_SNAKE_CASE: {v}"
            )
        return v
```

**Common validators:**
- **Military datetime ID:** `{PREFIX}_YYYYMMDD_HHMMSS_hash` pattern
- **UTC timestamp:** Convert naive to UTC, ensure timezone-aware
- **UPPER_SNAKE_CASE:** Signal types, event names
- **BASE/QUOTE format:** Asset pairs (`BTC/USDT`, `ETH/EUR`)
- **Decimal ranges:** Positive values, percentage bounds

### 6. model_config (REQUIRED)

```python
    model_config = {
        "frozen": True,  # Immutable DTOs preferred (use False if mutable needed)
        "str_strip_whitespace": True,
        "validate_assignment": True,
        "extra": "forbid",  # No extra fields allowed
        "json_schema_extra": {
            "examples": [
                {
                    "description": "{Use case 1 - describe scenario}",
                    "{dto}_id": "{PREFIX}_20251027_100001_a1b2c3d4",
                    "timestamp": "2025-10-27T10:00:01Z",
                    "field1": "value1",
                    "field2": "123.45",
                    # ... all required fields
                },
                {
                    "description": "{Use case 2 - describe scenario}",
                    "{dto}_id": "{PREFIX}_20251027_143000_e5f6g7h8",
                    "timestamp": "2025-10-27T14:30:00Z",
                    "field1": "value2",
                    "field2": "456.78",
                    # ... show optional fields in action
                },
                {
                    "description": "{Use case 3 - edge case/variant}",
                    "{dto}_id": "{PREFIX}_20251027_150500_i9j0k1l2",
                    "timestamp": "2025-10-27T15:05:00Z",
                    "field1": "value3",
                    # ... demonstrate defaults/omissions
                }
            ]
        }
    }
```

**json_schema_extra Best Practices:**
- **Minimum 2-3 examples** covering different scenarios
- **Descriptions** explaining what each example demonstrates
- **Realistic data** (actual symbols like BTCUSDT, realistic prices)
- **Correct ID formats** (military datetime pattern)
- **Valid Decimals** as strings (`"123.45"` not `123.45`)
- **Show optional fields** in use (at least in one example)
- **Only existing fields** (update after refactoring)

## ID Prefix Conventions

Use these prefixes for typed IDs:

| Prefix | DTO | Purpose |
|--------|-----|---------|
| `TCK_` | N/A | Tick birth ID (from TickCacheManager) |
| `NWS_` | N/A | News birth ID (from NewsAdapter) |
| `SCH_` | N/A | Schedule birth ID (from Scheduler) |
| `OPP_` | OpportunitySignal | Opportunity detection |
| `THR_` | ThreatSignal | Threat detection |
| `STR_` | StrategyDirective | Strategy decision |
| `ENT_` | EntryPlan | Entry planning |
| `SZE_` | SizePlan | Size planning |
| `EXT_` | ExitPlan | Exit planning |
| `RTE_` | RoutingPlan | Routing planning (future) |
| `EXE_` | ExecutionDirective | Execution directive (future) |

## Causality Decision Tree

**Does your DTO need `causality: CausalityChain`?**

```
Is this a pipeline DTO?
├─ YES → Is it a sub-planner output (EntryPlan, SizePlan, ExitPlan)?
│   ├─ YES → ❌ NO causality (receives StrategyDirective with causality)
│   └─ NO → Is it a top-level worker output or aggregation?
│       ├─ YES → ✅ HAS causality (OpportunitySignal, ThreatSignal, StrategyDirective)
│       └─ NO → Is it an execution DTO (ExecutionDirective)?
│           ├─ YES → ✅ HAS causality (PlanningAggregator adds plan IDs)
│           └─ NO → ❌ NO causality (flow control, platform DTOs)
└─ NO → ❌ NO causality (DispositionEnvelope, platform DTOs)
```

**DTOs WITH causality:**
- ✅ OpportunitySignal, ThreatSignal
- ✅ StrategyDirective (Strategy output)
- ✅ ExecutionDirective (Execution input - aggregated)

**DTOs WITHOUT causality:**
- ❌ EntryPlan, SizePlan, ExitPlan, RoutingPlan (sub-planners)
- ❌ DispositionEnvelope (flow control)
- ❌ Platform DTOs (not pipeline data)

## Frozen vs Mutable

**Use `"frozen": True` (immutable) when:**
- Pure data containers (signals, assessments)
- Never modified after creation
- Thread-safe sharing needed

**Use `"frozen": False` (mutable) when:**
- Plans that may be adjusted (EntryPlan, SizePlan, ExitPlan)
- Incremental updates during processing
- Validation on assignment needed (`"validate_assignment": True`)

**Default:** Prefer `frozen=True` unless you have specific reason for mutability.

## Complete Example

See these reference implementations:
- [opportunity_signal.md](./opportunity_signal.md) - Signal DTO with causality
- [entry_plan.md](./entry_plan.md) - Plan DTO without causality (lean spec)

## Checklist

Before committing new DTO:

- [ ] File header complete with @layer, @dependencies, @responsibilities
- [ ] Imports in 3 groups (Standard, Third-party, Project) with comments
- [ ] Class docstring with responsibilities, NOT responsibilities, usage example
- [ ] Fields ordered: causality → ID → timestamp → core → optional
- [ ] ID validator with military datetime pattern
- [ ] Timestamp validator ensuring UTC (if applicable)
- [ ] `model_config` with `json_schema_extra` (2-3 examples minimum)
- [ ] Examples use realistic data and correct ID formats
- [ ] Causality decision correct (check decision tree)
- [ ] Frozen/mutable decision documented
- [ ] All fields documented in docstring attributes section

## Related Documentation

- [DTO_TEST_TEMPLATE.md](../testing/DTO_TEST_TEMPLATE.md) - Test template
- [opportunity_signal.md](./opportunity_signal.md) - Reference example
- [entry_plan.md](./entry_plan.md) - Lean spec example
- [../../coding_standards/CODE_STYLE.md](../../coding_standards/CODE_STYLE.md) - Code style guide
- [../../architecture/POINT_IN_TIME_MODEL.md](../../architecture/POINT_IN_TIME_MODEL.md) - DTO philosophy
