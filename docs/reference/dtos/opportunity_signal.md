# OpportunitySignal DTO - Reference Implementation

## Overview

**File:** `backend/dtos/strategy/opportunity_signal.py`
**Tests:** `tests/unit/dtos/strategy/test_opportunity_signal.py`

OpportunitySignal is the **reference implementation** for Strategy DTOs with causality tracking. Use this as a template when creating new SWOT signal DTOs.

## Quick Facts

| Attribute | Value |
|-----------|-------|
| **Layer** | DTO (Strategy) |
| **Purpose** | OpportunityWorker output contract |
| **Causality** | ✅ Has CausalityChain |
| **Frozen** | ✅ Immutable |
| **Tests** | 22 comprehensive tests |
| **Quality** | 10/10 all gates |

## Architecture Context

**SWOT Framework Position:**
- ContextWorkers → BaseContext (Strengths & Weaknesses)
- **OpportunityWorkers → OpportunitySignal (Opportunities)** ← This DTO
- ThreatWorkers → ThreatSignal (Threats)
- PlanningWorker → StrategyDirective (combines quadrants)

**Causal Chain:**
```
TickID → OpportunitySignal.opportunity_id → StrategyDirective.strategy_id
```

## Implementation Highlights

### 1. File Header (EXEMPLARY)

```python
# backend/dtos/strategy/opportunity_signal.py
"""
OpportunitySignal DTO: OpportunityWorker output contract.

Represents a detected trading opportunity in the SWOT analysis framework.
OpportunityWorkers emit OpportunitySignals to signal potential long/short
entries based on technical analysis patterns.

Part of SWOT framework:
- ContextWorkers → BaseContext (Strengths & Weaknesses)
- OpportunityWorkers → OpportunitySignal (Opportunities)
- ThreatWorkers → ThreatSignal (Threats)
- PlanningWorker → Confrontation Matrix (combines quadrants)

@layer: DTO (Strategy)
@dependencies: [pydantic, datetime, backend.utils.id_generators, backend.dtos.causality]
@responsibilities: [opportunity detection contract, causal tracking, SWOT confidence]
"""
```

**Why exemplary:**
- Clear purpose statement
- Architecture context (SWOT framework)
- Explicit responsibilities
- Complete @layer/@dependencies/@responsibilities

### 2. Field Organization (PERFECT)

```python
class OpportunitySignal(BaseModel):
    """OpportunityWorker output DTO representing a detected trading opportunity."""
    
    # 1. Causality tracking (FIRST)
    causality: CausalityChain = Field(
        description="Causality tracking - IDs from birth (tick/news/schedule)"
    )

    # 2. Primary identifier (SECOND)
    opportunity_id: str = Field(
        default_factory=generate_opportunity_id,
        pattern=r'^OPP_\d{8}_\d{6}_[0-9a-f]{8}$',
        description="Typed opportunity ID (military datetime format)"
    )

    # 3. Timestamp (THIRD)
    timestamp: datetime = Field(
        description="When the opportunity was detected (UTC)"
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
opportunity_id: str = Field(
    default_factory=generate_opportunity_id,
    pattern=r'^OPP_\d{8}_\d{6}_[0-9a-f]{8}$',
    description="Typed opportunity ID (military datetime format)"
)
```

**Pattern breakdown:**
- `OPP_` - Typed prefix (Opportunity)
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
                "description": "FVG breakout signal (LONG opportunity)",
                "opportunity_id": "OPP_20251027_100001_a1b2c3d4",
                "timestamp": "2025-10-27T10:00:01Z",
                "asset": "BTCUSDT",
                "direction": "LONG",
                "signal_type": "FVG_BREAKOUT",
                "confidence": 0.85
            },
            {
                "description": "MSS reversal signal (SHORT opportunity)",
                "opportunity_id": "OPP_20251027_143000_e5f6g7h8",
                "timestamp": "2025-10-27T14:30:00Z",
                "asset": "ETHUSDT",
                "direction": "SHORT",
                "signal_type": "MSS_REVERSAL",
                "confidence": 0.72
            },
            {
                "description": "High confidence breakout (no confidence defaults to None)",
                "opportunity_id": "OPP_20251027_150500_i9j0k1l2",
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

**File:** `tests/unit/dtos/strategy/test_opportunity_signal.py`

**Test organization:**

```python
class TestOpportunitySignalCreation:
    """Test suite for OpportunitySignal instantiation."""
    # 4 tests: minimal, with confidence, ID auto-gen, custom ID

class TestOpportunitySignalOpportunityIDValidation:
    """Test suite for opportunity_id validation."""
    # 2 tests: valid format, invalid prefix

class TestOpportunitySignalTimestampValidation:
    """Test suite for timestamp validation."""
    # 3 tests: naive, aware UTC, non-UTC conversion

class TestOpportunitySignalAssetValidation:
    """Test suite for asset validation."""
    # 4 tests: valid format, missing slash, too short, too long

class TestOpportunitySignalSignalTypeValidation:
    """Test suite for signal_type validation."""
    # 5 tests: valid, lowercase, reserved SYSTEM_, reserved INTERNAL_, invalid chars

class TestOpportunitySignalConfidenceValidation:
    """Test suite for confidence validation."""
    # 3 tests: valid range, below 0.0, above 1.0

class TestOpportunitySignalImmutability:
    """Test suite for OpportunitySignal immutability."""
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

signal = OpportunitySignal(
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
opportunity_id = str(signal.opportunity_id)
assert opportunity_id.startswith("OPP_")
```

### 3. Validator Error Testing

```python
def test_invalid_value_rejected(self):
    """Test that invalid value is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        OpportunitySignal(
            causality=CausalityChain(tick_id=generate_tick_id()),
            field="invalid"
        )
    
    # Verify error message contains field name
    assert "field" in str(exc_info.value)
```

## Usage Example

```python
# Worker emitting OpportunitySignal
from backend.core.strategy_cache import strategy_cache
from backend.dtos.strategy.opportunity_signal import OpportunitySignal
from backend.dtos.causality import CausalityChain

class FVGOpportunityWorker:
    def process(self, tick: RawTick) -> DispositionEnvelope:
        # Get run anchor from cache
        anchor = strategy_cache.get_run_anchor()
        
        # Detect FVG pattern
        if self._detect_fvg(tick):
            signal = OpportunitySignal(
                causality=CausalityChain(tick_id=tick.tick_id),
                timestamp=anchor.timestamp,
                asset=tick.symbol,
                direction="long",
                signal_type="FVG_BREAKOUT",
                confidence=0.85
            )
            
            # Store in cache
            strategy_cache.set_dto("opportunity_signals", signal)
            
            return DispositionEnvelope(
                disposition=Disposition.PUBLISH,
                event_name="OPPORTUNITY_DETECTED",
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

- [ ] File header with @layer/@dependencies/@responsibilities (see OpportunitySignal)
- [ ] Imports in 3 groups with comments
- [ ] Causality field first (if applicable - check decision tree)
- [ ] Primary ID with military datetime pattern
- [ ] Timestamp with UTC validator (if applicable)
- [ ] All validators follow OpportunitySignal patterns
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
- **Source:** `backend/dtos/strategy/opportunity_signal.py`
- **Tests:** `tests/unit/dtos/strategy/test_opportunity_signal.py`
