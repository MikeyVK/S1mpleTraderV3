# Signal DTO - Reference Implementation

## Overview

**File:** `backend/dtos/strategy/signal.py`
**Tests:** `tests/unit/dtos/strategy/test_signal.py`

Signal is the **reference implementation** for Strategy DTOs with causality tracking. Use this as a template when creating new signal DTOs.

## Quick Facts

| Attribute | Value |
|-----------|-------|
| **Layer** | DTO (Strategy) |
| **Purpose** | SignalDetector output contract |
| **Causality** | ✅ Has CausalityChain |
| **Frozen** | ✅ Immutable |
| **Tests** | 22 comprehensive tests |
| **Quality** | 10/10 all gates |

## Architecture Context

**Signal Framework Position:**
- ContextWorkers → BaseContext (Strengths & Weaknesses)
- **SignalDetectors → Signal (Opportunities)** ← This DTO
- RiskMonitors → Risk (Risks)
- PlanningWorker → StrategyDirective (combines quadrants)

**Causal Chain:**
```
TickID → Signal.signal_id → StrategyDirective.strategy_id
```

## Implementation Highlights

### 1. File Header (EXEMPLARY)

```python
# backend/dtos/strategy/signal.py
"""
Signal DTO: SignalDetector output contract.

Represents a detected trading signal in the quant framework.
SignalDetectors emit Signals to signal potential long/short
entries based on technical analysis patterns.

Part of signal framework:
- ContextWorkers → BaseContext (Strengths & Weaknesses)
- SignalDetectors → Signal (Opportunities)
- RiskMonitors → Risk (Risks)
- PlanningWorker → Confrontation Matrix (combines quadrants)

@layer: DTO (Strategy)
@dependencies: [pydantic, datetime, backend.utils.id_generators, backend.dtos.causality]
@responsibilities: [signal detection contract, causal tracking, confidence scoring]
"""
```

**Why exemplary:**
- Clear purpose statement
- Architecture context (SWOT framework)
- Explicit responsibilities
- Complete @layer/@dependencies/@responsibilities

### 2. Field Organization (PERFECT)

```python
class Signal(BaseModel):
    """SignalDetector output DTO representing a detected trading signal."""
    
    # 1. Causality tracking (FIRST)
    causality: CausalityChain = Field(
        description="Causality tracking - IDs from birth (tick/news/schedule)"
    )

    # 2. Primary identifier (SECOND)
    signal_id: str = Field(
        default_factory=generate_signal_id,
        pattern=r'^SIG_\d{8}_\d{6}_[0-9a-f]{8}$',
        description="Typed signal ID (military datetime format)"
    )

    # 3. Timestamp (THIRD)
    timestamp: datetime = Field(
        description="When the signal was detected (UTC)"
    )

    # 4. Core data fields (logical grouping)
    asset: str = Field(...)
    direction: Literal["long", "short"] = Field(...)
    signal_type: str = Field(...)
    
    # 5. Optional fields (LAST)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, ...)
```

**Perfect because:**
- Causality always first (if applicable)
- Primary ID second
- Timestamp third
- Core fields grouped logically
- Optional fields last

### 3. Military Datetime ID Validation (REFERENCE)

```python
signal_id: str = Field(
    default_factory=generate_signal_id,
    pattern=r'^SIG_\d{8}_\d{6}_[0-9a-f]{8}$',
    description="Typed signal ID (military datetime format)"
)
```

**Pattern breakdown:**
- `SIG_` - Typed prefix (Signal)
- `\d{8}` - Date (YYYYMMDD)
- `\d{6}` - Time (HHMMSS)
- `[0-9a-f]{8}` - 8-char hex hash

**Tests cover:**
- ✅ Auto-generation if not provided
- ✅ Custom ID accepted if valid format
- ✅ Invalid prefix rejected
- ✅ Malformed format rejected

### 4. UTC Timestamp Validation (CANONICAL)

```python
@field_validator('timestamp')
@classmethod
def ensure_utc_timezone(cls, v: datetime) -> datetime:
    """Ensure timestamp is timezone-aware and in UTC."""
    if v.tzinfo is None:
        return v.replace(tzinfo=timezone.utc)
    return v.astimezone(timezone.utc)
```

**Handles 3 cases:**
1. Naive datetime → Add UTC timezone
2. UTC datetime → Pass through
3. Non-UTC datetime → Convert to UTC

**Tests cover:**
- ✅ Naive datetime converted to UTC
- ✅ Aware UTC datetime preserved
- ✅ Non-UTC datetime converted to UTC

### 5. UPPER_SNAKE_CASE Validation (ADVANCED)

```python
@field_validator('signal_type')
@classmethod
def validate_signal_type_format(cls, v: str) -> str:
    """Validate UPPER_SNAKE_CASE format and reserved prefixes."""
    
    # Check reserved prefixes first
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

**Advanced features:**
- Reserved prefix checking (SYSTEM_, INTERNAL_, _)
- UPPER_SNAKE_CASE regex pattern
- Clear error messages

**Tests cover:**
- ✅ Valid UPPER_SNAKE_CASE accepted
- ✅ lowercase rejected
- ✅ Reserved prefixes rejected
- ✅ Invalid characters rejected

### 6. json_schema_extra Examples (BEST PRACTICE)

```python
model_config = {
    "frozen": True,
    "extra": "forbid",
    "json_schema_extra": {
        "examples": [
            {
                "description": "FVG breakout signal (LONG signal)",
                "signal_id": "SIG_20251027_100001_a1b2c3d4",
                "timestamp": "2025-10-27T10:00:01Z",
                "asset": "BTCUSDT",
                "direction": "LONG",
                "signal_type": "FVG_BREAKOUT",
                "confidence": 0.85
            },
            {
                "description": "MSS reversal signal (SHORT signal)",
                "signal_id": "SIG_20251027_143000_e5f6g7h8",
                "timestamp": "2025-10-27T14:30:00Z",
                "asset": "ETHUSDT",
                "direction": "SHORT",
                "signal_type": "MSS_REVERSAL",
                "confidence": 0.72
            },
            {
                "description": "High confidence breakout (no confidence defaults to None)",
                "signal_id": "SIG_20251027_150500_i9j0k1l2",
                "timestamp": "2025-10-27T15:05:00Z",
                "asset": "SOLUSDT",
                "direction": "LONG",
                "signal_type": "TREND_CONTINUATION"
            }
        ]
    }
}
```

**Best practices demonstrated:**
- 3 examples covering different scenarios
- Descriptions explaining use case
- Realistic data (BTCUSDT, ETHUSDT, SOLUSDT)
- Correct ID formats (military datetime)
- Shows optional field usage (confidence present/absent)
- Valid Decimals as strings (where applicable)

## Test Structure (REFERENCE)

**File:** `tests/unit/dtos/strategy/test_signal.py`

**Test organization:**

```python
class TestSignalCreation:
    """Test suite for Signal instantiation."""
    # 4 tests: minimal, with confidence, ID auto-gen, custom ID

class TestSignalIDValidation:
    """Test suite for signal_id validation."""
    # 2 tests: valid format, invalid prefix

class TestSignalTimestampValidation:
    """Test suite for timestamp validation."""
    # 3 tests: naive, aware UTC, non-UTC conversion

class TestSignalAssetValidation:
    """Test suite for asset validation."""
    # 4 tests: valid format, missing slash, too short, too long

class TestSignalSignalTypeValidation:
    """Test suite for signal_type validation."""
    # 5 tests: valid, lowercase, reserved SYSTEM_, reserved INTERNAL_, invalid chars

class TestSignalConfidenceValidation:
    """Test suite for confidence validation."""
    # 3 tests: valid range, below 0.0, above 1.0

class TestSignalImmutability:
    """Test suite for Signal immutability."""
    # 2 tests: frozen fields, no extra fields
```

**Total:** 22 comprehensive tests

**Why reference:**
- Logical test class organization
- Descriptive class/method names
- Clear test intent in docstrings
- Complete validation coverage
- Uses `getattr()` pattern for Pydantic field access

## Key Patterns to Reuse

### 1. Causality Integration

```python
# In DTO
from backend.dtos.causality import CausalityChain

causality: CausalityChain = Field(
    description="Causality tracking - IDs from birth (tick/news/schedule)"
)

# In tests
from backend.utils.id_generators import generate_tick_id

signal = Signal(
    causality=CausalityChain(tick_id=generate_tick_id()),
    # ... other fields
)
```

### 2. getattr() for Pydantic Field Access

```python
# ✅ PREFERRED - Use getattr() to avoid Pylance warnings
causality = cast(CausalityChain, signal.causality)
assert getattr(causality, "tick_id") is not None
assert getattr(causality, "tick_id").startswith("TCK_")

# ✅ ACCEPTABLE - Intermediate variable
signal_id = str(signal.signal_id)
assert signal_id.startswith("SIG_")
```

### 3. Validator Error Testing

```python
def test_invalid_value_rejected(self):
    """Test that invalid value is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        Signal(
            causality=CausalityChain(tick_id=generate_tick_id()),
            field="invalid"
        )
    
    # Verify error message contains field name
    assert "field" in str(exc_info.value)
```

## Usage Example

```python
# Worker emitting Signal
from backend.core.strategy_cache import strategy_cache
from backend.dtos.strategy.signal import Signal
from backend.dtos.causality import CausalityChain

class FVGSignalDetector:
    def process(self, tick: RawTick) -> DispositionEnvelope:
        # Get run anchor from cache
        anchor = strategy_cache.get_run_anchor()
        
        # Detect FVG pattern
        if self._detect_fvg(tick):
            signal = Signal(
                causality=CausalityChain(tick_id=tick.tick_id),
                timestamp=anchor.timestamp,
                asset=tick.symbol,
                direction="long",
                signal_type="FVG_BREAKOUT",
                confidence=0.85
            )
            
            # Store in cache
            strategy_cache.set_dto("signals", signal)
            
            return DispositionEnvelope(
                disposition=Disposition.PUBLISH,
                event_name="SIGNAL_DETECTED",
                payload=signal
            )
        
        return DispositionEnvelope(disposition=Disposition.CONTINUE)
```

## Quality Metrics

| Metric | Value |
|--------|-------|
| **Lines of Code** | 158 (DTO) |
| **Tests** | 22 |
| **Test Coverage** | 100% |
| **Pylint Score** | 10.00/10 |
| **Mypy** | 0 errors (DTO only) |
| **Import Groups** | ✅ 3 groups with comments |
| **Docstrings** | ✅ Complete |
| **json_schema_extra** | ✅ 3 examples |

## Checklist for New DTOs

Use this checklist when creating new Strategy DTOs:

- [ ] File header with @layer/@dependencies/@responsibilities (see Signal)
- [ ] Imports in 3 groups with comments
- [ ] Causality field first (if applicable - check decision tree)
- [ ] Primary ID with military datetime pattern
- [ ] Timestamp with UTC validator (if applicable)
- [ ] All validators follow Signal patterns
- [ ] json_schema_extra with 2-3 realistic examples
- [ ] Test file with pyright suppressions
- [ ] Test classes organized by aspect (Creation, Validation, etc.)
- [ ] Tests use getattr() for Pydantic field access
- [ ] 20-30 comprehensive tests covering all validators
- [ ] Quality gates: 10/10 all gates

## Related Documentation

- **Template:** [STRATEGY_DTO_TEMPLATE.md](./STRATEGY_DTO_TEMPLATE.md)
- **Test Template:** [DTO_TEST_TEMPLATE.md](../testing/DTO_TEST_TEMPLATE.md)
- **Code Style:** [../../coding_standards/CODE_STYLE.md](../../coding_standards/CODE_STYLE.md)
- **Architecture:** [Point-in-Time Model](../../architecture/POINT_IN_TIME_MODEL.md)
- **Source:** `backend/dtos/strategy/signal.py`
- **Tests:** `tests/unit/dtos/strategy/test_signal.py`
