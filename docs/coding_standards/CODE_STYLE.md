# Code Style Guide

## Overview

> **⚠️ Read first:** [ARCHITECTURE_PRINCIPLES.md](ARCHITECTURE_PRINCIPLES.md) — the binding architectural contract. The style rules in this document are *form*; the architectural principles are *law*.

Code formatting rules are enforced automatically by `ruff` in the quality gates — they are not a cognitive burden for the developer. Architectural correctness (SOLID, DRY, Config-First, Fail-Fast) is the primary quality measure.

**PEP 8 compliance** is enforced by `ruff` — no need to memorize it. This document describes the residual manual conventions for file headers, import organization, docstrings, and patterns not covered by tooling.

## File Headers

All Python modules should include a standardized header. If your project uses code generation tooling, headers are generated automatically — manual addition is only required for non-generated files.

### Header Template

```python
# {relative_path_from_project_root}
"""
{Short title - Functionality}.

{Extended description of what this module does}

@layer: {Backend/Tests/Service/Frontend}
@dependencies: [{list, of, dependencies}]
@responsibilities:
    - {Responsibility 1}
    - {Responsibility 2}
"""
```

**Implementation:**
- ✅ **Generated files**: Headers auto-generated via code generation tooling
- ⚠️ **Non-generated files**: Must manually add header (rare cases only)

### Examples

**Component Module (Auto-generated):**
```python
# backend/services/order_processor.py
"""
Order Processor - Order lifecycle management.

Handles order creation, validation, and state transitions.

@layer: Backend (Services)
@dependencies: [pydantic, typing]
@responsibilities:
    - Validate order input
    - Persist order state
    - Emit order lifecycle events
```

**Test Module (Auto-generated):**
```python
# tests/unit/services/test_order_processor.py
"""
Unit tests for OrderProcessor.

Tests order lifecycle management according to TDD principles.

@layer: Tests (Unit)
@dependencies: [pytest, pydantic, backend.services.order_processor]
```

**Note:** Test modules typically don't include @responsibilities as their purpose is self-evident (test the module under test).

**Utility Module (Manual header required):**
```python
# backend/utils/id_generators.py
"""
Typed ID generation utilities.

Provides standardized ID generation with type prefixes for causal
traceability across the system.

@layer: Backend (Utils)
@dependencies: [uuid]
@responsibilities:
    - Generate typed IDs with consistent prefixes
    - Extract ID type from typed ID string
    - Maintain ID format consistency
"""
```

**Why This Convention:**
- **Tooling enforcement** - Automatic for all generated files
- **Quick navigation** - Immediately see where you are in the architecture
- **Documentation** - Explicit dependencies and responsibilities visible
- **Consistency** - All modules follow the same pattern
- **IDE-friendly** - File path as first line helps with context

## Import Organization

Imports must be grouped into **3 sections** with comment headers:

```python
# Standard library
from datetime import datetime, timezone
from typing import Literal

# Third-party
from pydantic import BaseModel, Field, field_validator

# Project modules
from backend.utils.id_generators import generate_signal_id
from backend.dtos.causality import CausalityChain
```

**Rules:**
1. **Standard library** - Python built-in modules
2. **Third-party** - External packages (pydantic, pytest, etc.)
3. **Project modules** - Local imports from `backend/` or `tests/`
4. Blank line between each group
5. Alphabetical order within each group
6. **Never import inside functions** - All imports at module top-level

**Implementation:**
- ✅ **Scaffolded files**: Import structure auto-generated via templates
- ⚠️ **Non-scaffolded files**: Must manually organize imports
- ✅ **Ruff autofix**: Can organize imports automatically (`ruff check --select I --fix`)

**Common violation:**
```python
# ❌ WRONG - import inside function
def my_function():
    from datetime import datetime  # NEVER DO THIS
    return datetime.now()

# ✅ CORRECT - import at top (enforced by scaffolding templates)
from datetime import datetime

def my_function():
    return datetime.now()
```

## Docstring Conventions

### Module Docstrings

**Comprehensive** documentation at module level (see File Headers section).

### Class Docstrings

**Concise** one-line summary:

```python
class Signal(BaseModel):
    """System DTO for signal detection output."""
```

**Not this:**
```python
class Signal(BaseModel):
    """
    This is the Signal class which represents
    a trading signal that has been detected by the
    SignalDetector and needs to be processed by...
    """  # TOO VERBOSE - details belong in module docstring
```

### Method Docstrings

**Brief and to-the-point:**

```python
@field_validator('timestamp')
@classmethod
def ensure_utc_timezone(cls, v: datetime) -> datetime:
    """Ensure timestamp is timezone-aware and in UTC."""
    if v.tzinfo is None:
        return v.replace(tzinfo=timezone.utc)
    return v.astimezone(timezone.utc)
```

**Not this:**
```python
@field_validator('timestamp')
@classmethod
def ensure_utc_timezone(cls, v: datetime) -> datetime:
    """
    This validator method ensures that the timestamp field is
    timezone-aware and converts it to UTC if needed. If the
    timestamp has no timezone info, it adds UTC. If it has a
    different timezone, it converts to UTC.
    
    Args:
        v: The datetime value to validate
        
    Returns:
        The validated datetime in UTC
        
    Raises:
        ValidationError: If conversion fails
    """
    # TOO VERBOSE for simple validators
```

**Guideline:** Module docs = detailed, class/method docs = compact.

## Line Length

**Maximum:** 100 characters

Configure VS Code ruler:
```json
{
    "editor.rulers": [100]
}
```

**Techniques to stay under limit:**

**1. Intermediate variables for long assertions:**
```python
# ❌ Line too long
assert dto.some_very_long_field_name == expected_very_long_value_name  # 102 chars

# ✅ Use intermediate variable
field_value = dto.some_very_long_field_name
assert field_value == expected_very_long_value_name
```

**2. Line continuation for long strings:**
```python
# ❌ Line too long
description = "This is a very long description that exceeds the 100 character limit and needs to be split"

# ✅ Use line continuation
description = (
    "This is a very long description that exceeds the 100 character "
    "limit and needs to be split"
)
```

**3. Break method chains:**
```python
# ❌ Line too long
result = dataframe.filter(condition).groupby('symbol').agg({'price': 'mean'}).reset_index()

# ✅ Break across lines
result = (
    dataframe
    .filter(condition)
    .groupby('symbol')
    .agg({'price': 'mean'})
    .reset_index()
)
```

## Whitespace Rules

**No trailing whitespace** - Lines must not end with spaces or tabs.

**Auto-fix:**
```powershell
(Get-Content backend/dtos/strategy/my_dto.py) | ForEach-Object { $_.TrimEnd() } | Set-Content backend/dtos/strategy/my_dto.py
```

**VS Code setting:**
```json
{
    "files.trimTrailingWhitespace": true,
    "files.insertFinalNewline": true
}
```

## Type Hinting

**Mandatory for all functions and methods:**

```python
# ✅ CORRECT - full type hints
def calculate_position_size(
    account_balance: Decimal,
    risk_percent: Decimal,
    stop_distance: Decimal
) -> Decimal:
    """Calculate position size based on risk parameters."""
    return (account_balance * risk_percent) / stop_distance

# ❌ WRONG - no type hints
def calculate_position_size(account_balance, risk_percent, stop_distance):
    return (account_balance * risk_percent) / stop_distance
```

**Use modern type hints (Python 3.10+):**
```python
# ✅ CORRECT - modern syntax
def process_signals(signals: list[Signal]) -> dict[str, Any]:
    ...

# ❌ OLD STYLE - avoid (but still works)
from typing import List, Dict, Any
def process_signals(signals: List[Signal]) -> Dict[str, Any]:
    ...
```

## Pydantic DTO Conventions

### Field Order

1. **Causality tracking** (if applicable) - Always first field
2. **Primary identifier** (e.g., `signal_id`, `plan_id`)
3. **Core data fields** (alphabetical or logical grouping)
4. **Optional fields** (at end)

```python
class Signal(BaseModel):
    """System DTO for signal detection output."""
    
    # 1. Causality tracking
    causality: CausalityChain = Field(
        description="Causality tracking from tick through worker chain"
    )
    
    # 2. Primary identifier
    signal_id: str = Field(default_factory=generate_signal_id)
    
    # 3. Core data fields
    symbol: str
    direction: Literal["BUY", "SELL"]
    confidence: Decimal
    
    # 4. Optional fields
    metadata: dict[str, Any] | None = None
```

### json_schema_extra Examples

**REQUIRED** for all DTOs - provides self-documentation for OpenAPI/Swagger.

**Minimum:** 2-3 examples covering different use cases.

```python
model_config = {
    "frozen": False,
    "str_strip_whitespace": True,
    "validate_assignment": True,
    "json_schema_extra": {
        "examples": [
            {
                "description": "Market entry (WHAT/WHERE only)",
                "plan_id": "ENT_20251027_143052_a1b2c3d4",
                "symbol": "BTCUSDT",
                "direction": "BUY",
                "order_type": "MARKET"
            },
            {
                "description": "Limit entry at specific price",
                "plan_id": "ENT_20251027_143053_e5f6g7h8",
                "symbol": "ETHUSDT",
                "direction": "SELL",
                "order_type": "LIMIT",
                "limit_price": "3510.00"
            },
            {
                "description": "Stop-limit for breakout",
                "plan_id": "ENT_20251027_143054_i9j0k1l2",
                "symbol": "SOLUSDT",
                "direction": "BUY",
                "order_type": "STOP_LIMIT",
                "stop_price": "125.00",
                "limit_price": "125.50"
            }
        ]
    }
}
```

**Best practices:**
- **Multiple examples** - Cover different scenarios
- **Descriptions** - Explain what each example demonstrates
- **Realistic data** - Use actual symbols (BTCUSDT, ETHUSDT), realistic prices
- **Correct ID formats** - Military datetime pattern
- **Valid Decimals** - As strings ("125.00" not 125.00)
- **Only existing fields** - Don't show removed fields after refactoring

**When to skip:**
- Internal helper classes (not exported via API)
- Abstract base classes without instances
- Config classes that only use YAML

## Contract-Driven Development

**CRITICAL PRINCIPLE:** All data exchange via strict Pydantic contracts.

```python
# ✅ GOOD - Explicit DTO
from pydantic import BaseModel

class MyOutputDTO(BaseModel):
    value: float
    confidence: float
    timestamp: datetime

def my_function() -> MyOutputDTO:
    return MyOutputDTO(value=1.23, confidence=0.85, timestamp=datetime.now())

# ❌ BAD - Primitive types or dicts
def bad_function() -> dict:
    return {'value': 1.23}  # No type safety!
```

**Why DTOs:**
- **Type safety** - Catch errors at design time
- **Validation** - Pydantic enforces constraints
- **Documentation** - Self-documenting with `json_schema_extra`
- **API contracts** - Clear interfaces between components

## Logging & Traceability

### Structured Logging

Primary log: `run.log.json` for analysis

**Use typed IDs for traceability:**
- `TCK_*` - Tick ID (birth)
- `NWS_*` - News ID (birth)
- `SCH_*` - Schedule ID (birth)
- `SIG_*` - Signal ID
- `RSK_*` - Risk ID
- `STR_*` - Strategy directive ID
- `ENT_*` - Entry plan ID
- `SZE_*` - Size plan ID
- `EXT_*` - Exit plan ID
- `RTE_*` - Routing plan ID

### IJournalWriter

For significant events only, **NOT** for flow-data.

**Use for:**
- Trade lifecycle events (opened, closed)
- Strategy decisions (signal detected, risk assessed)
- Risk events (limit breached, emergency halt)

**Don't use for:**
- Every tick received
- Every DTO transformation
- Debug messages

## VS Code Configuration

Recommended `.vscode/settings.json`:

```json
{
    "files.trimTrailingWhitespace": true,
    "files.insertFinalNewline": true,
    "editor.rulers": [100],
    "python.analysis.typeCheckingMode": "basic",
    "editor.formatOnSave": false,
    "[python]": {
        "editor.defaultFormatter": "charliermarsh.ruff"
    }
}
```

## Anti-Patterns to Avoid

❌ **Primitive obsession** - Using dicts instead of DTOs

❌ **God classes** - Classes with too many responsibilities

❌ **Magic numbers** - Use named constants

❌ **Deep nesting** - Max 3 levels of indentation

❌ **Long functions** - Extract helper methods

❌ **Global state** - Use dependency injection

❌ **Premature optimization** - Get it working first

❌ **Missing type hints** - Required for all functions

❌ **Trailing whitespace** - Auto-fix before commit

❌ **Imports in functions** - Always at module top

## Related Documentation

- [TDD_WORKFLOW.md](TDD_WORKFLOW.md) - Test-driven development cycle
- [QUALITY_GATES.md](QUALITY_GATES.md) - Quality checklist
- [GIT_WORKFLOW.md](GIT_WORKFLOW.md) - Branching and commit conventions
- [../architecture/CORE_PRINCIPLES.md](../architecture/CORE_PRINCIPLES.md) - System design philosophy
