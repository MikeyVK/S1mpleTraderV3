# ExecutionIntent DTO - Conceptueel Ontwerp (STAP 0)

**Status:** Architectural Contract  
**Versie:** 1.0  
**Datum:** 2025-10-28  
**Owner:** Platform Architecture Team

---

## Executive Summary

**ExecutionIntent** is de connector-agnostic vervanger van RoutingPlan. Het DTO drukt **universele trade-offs** uit die door elke connector (CEX/DEX/Backtest) geïnterpreteerd kunnen worden, zonder connector-specifieke concepten te lekken naar de strategy layer.

**Kernprincipe:**
> Strategy layer spreekt in **wat** bereikt moet worden (urgency, visibility, slippage),  
> ExecutionTranslator vertaalt naar **hoe** (time_in_force, iceberg, gas_strategy).

---

## 1. Architectural Contract

### 1.1 Responsibility (SRP)

**ExecutionIntent heeft ÉÉN verantwoordelijkheid:**
> "Express universal execution trade-offs that are connector-agnostic"

**NIET verantwoordelijk voor:**
- ❌ Connector-specifieke implementatie details (time_in_force, iceberg, gas)
- ❌ Order creation (dat is ExecutionHandler's domein)
- ❌ TWAP/VWAP algoritme parameters (dat is ExecutionTranslator's domein)
- ❌ Venue selection (dat is ExecutionTranslator's domein)

### 1.2 Universal Trade-Offs (Core Fields)

Alle connectors MOETEN deze concepten kunnen interpreteren:

| **Trade-off** | **Type** | **Range** | **Meaning** | **CEX Interpretation** | **DEX Interpretation** | **Backtest Interpretation** |
|--------------|----------|-----------|-------------|------------------------|------------------------|----------------------------|
| `execution_urgency` | Decimal | 0.0-1.0 | Patience vs Speed | 0.9 → MARKET/IOC<br/>0.2 → LIMIT/TWAP | 0.9 → FAST gas<br/>0.2 → SLOW gas | 0.9 → 10ms latency<br/>0.2 → 500ms latency |
| `visibility_preference` | Decimal | 0.0-1.0 | Stealth vs Transparency | 0.1 → iceberg orders<br/>0.7 → regular orders | 0.1 → private mempool<br/>0.7 → public broadcast | 0.1 → 0.5x impact<br/>0.7 → 1.0x impact |
| `max_slippage_pct` | Decimal | 0.0-1.0 | Hard price limit | Limit price range for TWAP | Slippage tolerance in swap | Rejects trades > limit |

**Rationale:** Deze 3 dimensies zijn universeel:
- **Urgency** - Alle connectors hebben tijd-geld afweging (Almgren-Chriss model)
- **Visibility** - Alle connectors hebben informatielekage vs executie-efficiëntie afweging
- **Slippage** - Alle connectors hebben prijs impact limits

### 1.3 Time Constraints (Optional Hard Limits)

| **Field** | **Type** | **Purpose** | **Example** |
|-----------|----------|-------------|-------------|
| `must_complete_immediately` | bool | Hard urgency constraint | Flash crash → True |
| `max_execution_window_minutes` | Optional[int] | Time window limit | 30 min max for position entry |

### 1.4 Hints (Optional Suggestions)

**BELANGRIJKE ONDERSCHEID:**

**Constraints** (MUST) vs **Hints** (MAY):

```python
# ✅ CONSTRAINT - Translator MOET respecteren
max_slippage_pct=Decimal("0.01")  # HARD limit - reject trade if > 1%
must_complete_immediately=True     # HARD constraint - now or fail

# ✅ HINT - Translator MAY interpreteren
preferred_execution_style="TWAP"   # Suggestie - translator kan negeren
chunk_count_hint=5                 # Suggestie - translator kan andere count kiezen
```

| **Hint** | **Type** | **Purpose** | **Binding?** |
|----------|----------|-------------|--------------|
| `preferred_execution_style` | Optional[str] | Execution style suggestie | NO - translator decides |
| `chunk_count_hint` | Optional[int] | Chunking suggestie | NO - translator calculates |
| `chunk_distribution` | Optional[str] | Distribution suggestie | NO - translator chooses |
| `min_fill_ratio` | Optional[Decimal] | Partial fill acceptance | NO - connector-specific |

**Rationale Hints:**
- Strategy kan execution expertise suggereren (bijv. "TWAP works well here")
- Translator heeft finale beslissing (bijv. connector ondersteunt geen TWAP)
- Type system voorkomt hard dependencies (Optional types)

### 1.5 Action Types

ExecutionIntent ondersteunt meerdere acties (niet alleen EXECUTE_TRADE):

```python
class ExecutionAction(str, Enum):
    EXECUTE_TRADE = "EXECUTE_TRADE"      # Open nieuwe trade
    CANCEL_ORDER = "CANCEL_ORDER"        # Cancel specifieke order
    MODIFY_ORDER = "MODIFY_ORDER"        # Wijzig bestaande order
    CANCEL_GROUP = "CANCEL_GROUP"        # Cancel execution group (TWAP)
```

**Use Cases:**
- `EXECUTE_TRADE` - Normale entry/exit
- `CANCEL_ORDER` - Emergency stop (flash crash)
- `MODIFY_ORDER` - Trailing stop adjustment
- `CANCEL_GROUP` - Cancel hele TWAP execution

---

## 2. Field-by-Field Specification

### 2.1 Required Fields

#### `intent_id: str`
- **Purpose:** Unique identifier
- **Format:** `"EXI_YYYYMMDD_HHMMSS_xxxxx"` (5 char random suffix)
- **Example:** `"EXI_20251028_143022_a8f3c"`
- **Validation:** Non-empty, matches pattern
- **Immutability:** Set at creation, never changes

#### `action: ExecutionAction`
- **Purpose:** What operation to perform
- **Values:** EXECUTE_TRADE, CANCEL_ORDER, MODIFY_ORDER, CANCEL_GROUP
- **Example:** `ExecutionAction.EXECUTE_TRADE`
- **Validation:** Must be valid enum value
- **Default:** NO DEFAULT (must be explicit)

#### `execution_urgency: Decimal`
- **Purpose:** Universal urgency level (patience vs speed)
- **Range:** `Decimal("0.0")` to `Decimal("1.0")`
- **Precision:** 2 decimal places (0.00 - 1.00)
- **Example:** `Decimal("0.82")` (high urgency)
- **Validation:** 
  - Must be between 0.0 and 1.0 (inclusive)
  - Must be Decimal (not float for precision)
- **Interpretation:**
  - `0.0-0.2` - Very patient (days)
  - `0.2-0.4` - Patient (hours)
  - `0.4-0.6` - Balanced (minutes to hour)
  - `0.6-0.8` - Urgent (minutes)
  - `0.8-1.0` - Very urgent (seconds)

#### `visibility_preference: Decimal`
- **Purpose:** Universal visibility level (stealth vs transparency)
- **Range:** `Decimal("0.0")` to `Decimal("1.0")`
- **Precision:** 2 decimal places
- **Example:** `Decimal("0.10")` (low visibility - stealth)
- **Validation:** Must be between 0.0 and 1.0
- **Interpretation:**
  - `0.0-0.2` - Maximum stealth (iceberg, private mempool)
  - `0.2-0.4` - Some stealth
  - `0.4-0.6` - Balanced
  - `0.6-0.8` - Some transparency
  - `0.8-1.0` - Full transparency (show full size)

#### `max_slippage_pct: Decimal`
- **Purpose:** Hard price impact limit
- **Range:** `Decimal("0.0")` to `Decimal("1.0")` (0% to 100%)
- **Precision:** 4 decimal places (0.0001 = 0.01%)
- **Example:** `Decimal("0.0050")` (0.5% max slippage)
- **Validation:** Must be >= 0.0 and <= 1.0
- **Enforcement:** Translator MUST reject if slippage > limit

### 2.2 Optional Constraints

#### `must_complete_immediately: bool`
- **Purpose:** Hard urgency constraint
- **Default:** `False`
- **Example:** `True` (flash crash emergency)
- **Validation:** Boolean
- **Enforcement:** If True, translator MUST execute now or fail

#### `max_execution_window_minutes: Optional[int]`
- **Purpose:** Maximum time window for execution
- **Default:** `None` (no limit)
- **Example:** `30` (complete within 30 minutes)
- **Validation:** If set, must be > 0
- **Enforcement:** Translator MUST complete or cancel within window

### 2.3 Optional Hints

#### `preferred_execution_style: Optional[str]`
- **Purpose:** Execution style suggestion
- **Default:** `None`
- **Values:** "TWAP", "VWAP", "ICEBERG", "POV" (Percentage of Volume)
- **Example:** `"TWAP"`
- **Validation:** If set, must be known style (warning if unknown)
- **Binding:** NO - translator decides

#### `chunk_count_hint: Optional[int]`
- **Purpose:** Suggested number of order chunks
- **Default:** `None`
- **Example:** `5` (split into 5 chunks)
- **Validation:** If set, must be >= 1
- **Binding:** NO - translator calculates optimal count

#### `chunk_distribution: Optional[str]`
- **Purpose:** Suggested chunk distribution strategy
- **Default:** `None`
- **Values:** "UNIFORM", "FRONT_LOADED", "BACK_LOADED", "RANDOM"
- **Example:** `"UNIFORM"`
- **Validation:** If set, must be known strategy
- **Binding:** NO - translator chooses

#### `min_fill_ratio: Optional[Decimal]`
- **Purpose:** Minimum acceptable fill ratio for partial fills
- **Default:** `None` (accept any fill)
- **Range:** `Decimal("0.0")` to `Decimal("1.0")`
- **Example:** `Decimal("0.80")` (accept if >= 80% filled)
- **Validation:** If set, must be between 0.0 and 1.0
- **Binding:** Connector-dependent (some don't support partial fills)

---

## 3. Validation Rules

### 3.1 Field-Level Validation

```python
# Urgency range
assert Decimal("0.0") <= execution_urgency <= Decimal("1.0")

# Visibility range
assert Decimal("0.0") <= visibility_preference <= Decimal("1.0")

# Slippage range
assert Decimal("0.0") <= max_slippage_pct <= Decimal("1.0")

# Execution window
if max_execution_window_minutes is not None:
    assert max_execution_window_minutes > 0

# Min fill ratio
if min_fill_ratio is not None:
    assert Decimal("0.0") <= min_fill_ratio <= Decimal("1.0")
```

### 3.2 Cross-Field Validation

```python
# High urgency + long execution window = inconsistent
if execution_urgency > Decimal("0.8"):
    if max_execution_window_minutes is not None:
        assert max_execution_window_minutes <= 5  # Max 5 min for high urgency

# Must complete immediately + execution window = conflict
if must_complete_immediately:
    assert max_execution_window_minutes is None  # No window if immediate
```

### 3.3 Action-Specific Validation

```python
# CANCEL_ORDER/CANCEL_GROUP don't need slippage/visibility
if action in [ExecutionAction.CANCEL_ORDER, ExecutionAction.CANCEL_GROUP]:
    # These fields may be ignored
    pass

# EXECUTE_TRADE needs all trade-offs
if action == ExecutionAction.EXECUTE_TRADE:
    assert execution_urgency is not None
    assert visibility_preference is not None
    assert max_slippage_pct is not None
```

---

## 4. Immutability Contract

ExecutionIntent is **frozen** (immutable after creation):

```python
@dataclass(frozen=True)
class ExecutionIntent:
    """Immutable execution intent - no modifications after creation."""
    pass
```

**Rationale:**
- Prevents accidental mutations during translation
- Enables safe concurrent processing
- Ensures audit trail integrity (intent = what strategy decided)

**Modification Pattern:**
```python
# ❌ WRONG - can't mutate
intent.execution_urgency = Decimal("0.9")  # TypeError!

# ✅ CORRECT - create new instance
updated_intent = dataclasses.replace(
    intent,
    execution_urgency=Decimal("0.9")
)
```

---

## 5. Example Instances

### 5.1 High Urgency Market Order

```python
ExecutionIntent(
    intent_id="EXI_20251028_143022_a8f3c",
    action=ExecutionAction.EXECUTE_TRADE,
    
    # High urgency trade
    execution_urgency=Decimal("0.90"),      # Very urgent (seconds)
    visibility_preference=Decimal("0.70"),  # Normal visibility
    max_slippage_pct=Decimal("0.0100"),    # 1% max slippage
    
    # Immediate execution required
    must_complete_immediately=True,
    max_execution_window_minutes=None,
    
    # No hints - let translator decide
    preferred_execution_style=None,
    chunk_count_hint=None,
    chunk_distribution=None,
    min_fill_ratio=None
)

# Expected CEX translation:
# → order_type="MARKET", time_in_force="IOC", chunk_count=1
```

### 5.2 Patient TWAP (Large Order)

```python
ExecutionIntent(
    intent_id="EXI_20251028_143025_b7c4d",
    action=ExecutionAction.EXECUTE_TRADE,
    
    # Low urgency, stealth
    execution_urgency=Decimal("0.20"),      # Very patient (hours)
    visibility_preference=Decimal("0.10"),  # High stealth
    max_slippage_pct=Decimal("0.0050"),    # 0.5% max slippage
    
    # Time window
    must_complete_immediately=False,
    max_execution_window_minutes=30,        # 30 min window
    
    # Hints for TWAP (translator may interpret)
    preferred_execution_style="TWAP",
    chunk_count_hint=5,
    chunk_distribution="UNIFORM",
    min_fill_ratio=Decimal("0.80")         # Accept if 80%+ filled
)

# Expected CEX translation:
# → order_type="LIMIT", time_in_force="GTC", iceberg=True, chunk_count=5
```

### 5.3 Emergency Cancel (Flash Crash)

```python
ExecutionIntent(
    intent_id="EXI_20251028_143030_c8e6f",
    action=ExecutionAction.CANCEL_GROUP,    # Cancel entire TWAP
    
    # Maximum urgency
    execution_urgency=Decimal("1.00"),      # NOW!
    visibility_preference=Decimal("0.50"),  # Don't care
    max_slippage_pct=Decimal("0.0"),       # N/A for cancel
    
    # Immediate execution
    must_complete_immediately=True,
    max_execution_window_minutes=None,
    
    # No hints needed for cancel
    preferred_execution_style=None,
    chunk_count_hint=None,
    chunk_distribution=None,
    min_fill_ratio=None
)

# Expected CEX translation:
# → Cancel all orders in execution group immediately
```

### 5.4 DEX Swap (Stealth + MEV Protection)

```python
ExecutionIntent(
    intent_id="EXI_20251028_143035_d9a7f",
    action=ExecutionAction.EXECUTE_TRADE,
    
    # Balanced urgency, high stealth
    execution_urgency=Decimal("0.50"),      # Balanced (minutes)
    visibility_preference=Decimal("0.05"),  # Maximum stealth
    max_slippage_pct=Decimal("0.0200"),    # 2% max (DEX has more slippage)
    
    # No immediate requirement
    must_complete_immediately=False,
    max_execution_window_minutes=10,        # 10 min window
    
    # No hints (DEX-specific routing is translator's job)
    preferred_execution_style=None,
    chunk_count_hint=None,
    chunk_distribution=None,
    min_fill_ratio=Decimal("1.0")          # All-or-nothing preferred
)

# Expected DEX translation:
# → gas_strategy="STANDARD", private_mempool=True, MEV_protection=True
```

### 5.5 Backtest Simulation

```python
ExecutionIntent(
    intent_id="EXI_20251028_143040_e1b8g",
    action=ExecutionAction.EXECUTE_TRADE,
    
    # Medium urgency for realistic simulation
    execution_urgency=Decimal("0.60"),      # Urgent (minutes)
    visibility_preference=Decimal("0.40"),  # Some stealth
    max_slippage_pct=Decimal("0.0075"),    # 0.75% max
    
    # No time constraints in backtest
    must_complete_immediately=False,
    max_execution_window_minutes=None,
    
    # No hints
    preferred_execution_style=None,
    chunk_count_hint=None,
    chunk_distribution=None,
    min_fill_ratio=None
)

# Expected Backtest translation:
# → fill_model="MARKET_IMPACT", latency_ms=100, impact_multiplier=0.6
```

---

## 6. Type System Guarantees

### 6.1 Compiler Enforced

```python
# ✅ Type-safe creation
intent = ExecutionIntent(
    intent_id="EXI_...",
    action=ExecutionAction.EXECUTE_TRADE,  # Enum enforced
    execution_urgency=Decimal("0.82"),     # Decimal enforced
    visibility_preference=Decimal("0.20"),
    max_slippage_pct=Decimal("0.01")
)

# ❌ Compiler error - wrong type
intent = ExecutionIntent(
    execution_urgency=0.82,  # TypeError: expected Decimal, got float
    ...
)

# ❌ Compiler error - missing required field
intent = ExecutionIntent(
    intent_id="EXI_...",
    action=ExecutionAction.EXECUTE_TRADE,
    # Missing execution_urgency → TypeError
)
```

### 6.2 Runtime Validation

```python
# Pydantic validators (runtime checks)
@validator('execution_urgency')
def validate_urgency_range(cls, v):
    if not (Decimal("0.0") <= v <= Decimal("1.0")):
        raise ValueError(f"urgency must be 0.0-1.0, got {v}")
    return v

@validator('max_slippage_pct')
def validate_slippage_range(cls, v):
    if not (Decimal("0.0") <= v <= Decimal("1.0")):
        raise ValueError(f"slippage must be 0.0-1.0, got {v}")
    return v
```

---

## 7. JSON Schema (OpenAPI)

### 7.1 Schema Definition

```json
{
  "title": "ExecutionIntent",
  "description": "Connector-agnostic execution trade-offs",
  "type": "object",
  "required": [
    "intent_id",
    "action",
    "execution_urgency",
    "visibility_preference",
    "max_slippage_pct"
  ],
  "properties": {
    "intent_id": {
      "type": "string",
      "pattern": "^EXI_\\d{8}_\\d{6}_[a-z0-9]{5}$",
      "example": "EXI_20251028_143022_a8f3c"
    },
    "action": {
      "type": "string",
      "enum": ["EXECUTE_TRADE", "CANCEL_ORDER", "MODIFY_ORDER", "CANCEL_GROUP"],
      "example": "EXECUTE_TRADE"
    },
    "execution_urgency": {
      "type": "number",
      "format": "decimal",
      "minimum": 0.0,
      "maximum": 1.0,
      "example": 0.82
    },
    "visibility_preference": {
      "type": "number",
      "format": "decimal",
      "minimum": 0.0,
      "maximum": 1.0,
      "example": 0.20
    },
    "max_slippage_pct": {
      "type": "number",
      "format": "decimal",
      "minimum": 0.0,
      "maximum": 1.0,
      "example": 0.0050
    },
    "must_complete_immediately": {
      "type": "boolean",
      "default": false
    },
    "max_execution_window_minutes": {
      "type": "integer",
      "minimum": 1,
      "nullable": true
    },
    "preferred_execution_style": {
      "type": "string",
      "enum": ["TWAP", "VWAP", "ICEBERG", "POV"],
      "nullable": true
    },
    "chunk_count_hint": {
      "type": "integer",
      "minimum": 1,
      "nullable": true
    },
    "chunk_distribution": {
      "type": "string",
      "enum": ["UNIFORM", "FRONT_LOADED", "BACK_LOADED", "RANDOM"],
      "nullable": true
    },
    "min_fill_ratio": {
      "type": "number",
      "format": "decimal",
      "minimum": 0.0,
      "maximum": 1.0,
      "nullable": true
    }
  }
}
```

### 7.2 Example JSON Instances

```json
{
  "intent_id": "EXI_20251028_143022_a8f3c",
  "action": "EXECUTE_TRADE",
  "execution_urgency": 0.90,
  "visibility_preference": 0.70,
  "max_slippage_pct": 0.0100,
  "must_complete_immediately": true,
  "max_execution_window_minutes": null,
  "preferred_execution_style": null,
  "chunk_count_hint": null,
  "chunk_distribution": null,
  "min_fill_ratio": null
}
```

---

## 8. Test Coverage Requirements

### 8.1 Minimum Test Cases (15+)

**Creation Tests (3):**
1. ✅ `test_execution_intent_creation_minimal` - Required fields only
2. ✅ `test_execution_intent_creation_full` - All fields populated
3. ✅ `test_execution_intent_creation_with_hints` - Optional hints

**Validation Tests (6):**
4. ✅ `test_urgency_validation_in_range` - Valid urgency values
5. ✅ `test_urgency_validation_out_of_range` - Invalid urgency → ValueError
6. ✅ `test_visibility_validation_in_range` - Valid visibility values
7. ✅ `test_visibility_validation_out_of_range` - Invalid visibility → ValueError
8. ✅ `test_slippage_validation_in_range` - Valid slippage values
9. ✅ `test_slippage_validation_out_of_range` - Invalid slippage → ValueError

**Action Tests (4):**
10. ✅ `test_action_execute_trade` - EXECUTE_TRADE action
11. ✅ `test_action_cancel_order` - CANCEL_ORDER action
12. ✅ `test_action_cancel_group` - CANCEL_GROUP action
13. ✅ `test_action_modify_order` - MODIFY_ORDER action

**Immutability Tests (2):**
14. ✅ `test_immutability_frozen` - Cannot mutate after creation
15. ✅ `test_immutability_replace` - dataclasses.replace() works

**JSON Serialization (1):**
16. ✅ `test_json_serialization_roundtrip` - to_json() → from_json()

---

## 9. Dependencies & Integration

### 9.1 Upstream Dependencies

**Created By:**
- `ExecutionIntentPlanner` (Strategy layer plugin)

**Input Dependencies:**
- `ExecutionRequest` (aggregated Entry + Size + Exit plans)
- `StrategyDirective` (hints from strategy)

### 9.2 Downstream Consumers

**Consumed By:**
- `ExecutionTranslator` (Platform layer)
  - CEXExecutionTranslator
  - DEXExecutionTranslator
  - BacktestExecutionTranslator

**Output Transformation:**
- ExecutionIntent → ConnectorExecutionSpec (CEX/DEX/Backtest specific)

### 9.3 Storage & Journaling

**StrategyJournal:**
- ExecutionIntent stored as decision artifact
- Linked to parent StrategyDirective
- Linked to resulting ExecutionDirective

**Causality Chain:**
```
OpportunitySignal
  → StrategyDirective
    → Entry/Size/Exit Plans
      → ExecutionIntent       ← This DTO
        → ConnectorExecutionSpec
          → ExecutionGroup + Orders
```

---

## 10. Breaking Changes from RoutingPlan

### 10.1 Removed Fields

| **OLD Field (RoutingPlan)** | **Reason for Removal** |
|----------------------------|------------------------|
| `timing: str` | Connector-specific → replaced by `execution_urgency` |
| `time_in_force: str` | CEX-only concept → moved to CEXExecutionSpec |
| `iceberg_preference: Decimal` | CEX-only → replaced by `visibility_preference` |
| `twap_duration_minutes: int` | Implementation detail → translator decides |
| `post_only_flag: bool` | CEX-only → moved to CEXExecutionSpec |

### 10.2 New Fields

| **NEW Field (ExecutionIntent)** | **Purpose** |
|--------------------------------|-------------|
| `action: ExecutionAction` | Support cancel/modify operations |
| `visibility_preference: Decimal` | Universal stealth concept (replaces iceberg) |
| `must_complete_immediately: bool` | Hard urgency constraint |
| `max_execution_window_minutes: Optional[int]` | Time window limit |
| `preferred_execution_style: Optional[str]` | Execution style hint |
| `chunk_count_hint: Optional[int]` | Chunking hint |
| `chunk_distribution: Optional[str]` | Distribution hint |
| `min_fill_ratio: Optional[Decimal]` | Partial fill acceptance |

### 10.3 Migration Example

```python
# ❌ OLD (v3.0) - RoutingPlan
old_plan = RoutingPlan(
    plan_id="ROU_...",
    timing="TWAP",                    # Connector-specific!
    time_in_force="GTC",              # CEX-only!
    max_slippage_pct=Decimal("0.01"),
    execution_urgency=Decimal("0.2"),
    iceberg_preference=Decimal("0.5") # CEX-only!
)

# ✅ NEW (v4.0) - ExecutionIntent
new_intent = ExecutionIntent(
    intent_id="EXI_...",
    action=ExecutionAction.EXECUTE_TRADE,
    
    # Universal trade-offs
    execution_urgency=Decimal("0.2"),      # From old execution_urgency
    visibility_preference=Decimal("0.5"),  # From old iceberg_preference
    max_slippage_pct=Decimal("0.01"),     # Same field
    
    # Optional hints (replaces timing="TWAP")
    preferred_execution_style="TWAP",
    chunk_count_hint=None,  # Translator decides
    chunk_distribution="UNIFORM"
)
```

---

## 11. Quality Criteria (Definition of Done)

### 11.1 Code Quality

- ✅ Pylint score: **10.0/10**
- ✅ Type hints: **100% coverage**
- ✅ Docstrings: All public methods
- ✅ Immutability: `@dataclass(frozen=True)`

### 11.2 Test Quality

- ✅ Test coverage: **100%** (all fields, all validators)
- ✅ Test count: **Minimum 15 tests**
- ✅ All tests pass: **GREEN**
- ✅ Edge cases covered (boundary values, None handling)

### 11.3 Documentation Quality

- ✅ JSON schema examples: **3+ examples**
- ✅ Docstring examples: Code examples in docstring
- ✅ Migration guide: RoutingPlan → ExecutionIntent mapping

---

## 12. Decision Log

### Decision 1: Why Decimal instead of float?

**Problem:** float heeft precision issues (0.1 + 0.2 != 0.3)

**Solution:** Decimal for all percentages/ratios

**Rationale:**
- Financial calculations require exact precision
- Slippage 0.01% vs 0.0099% matters in production
- Decimal("0.01") is unambiguous

**References:** Python Decimal documentation, IEEE 754 floating point

---

### Decision 2: Why hints are optional (not required)?

**Problem:** Not all strategies know optimal execution style

**Solution:** Hints are `Optional[...]` - translator has fallback logic

**Rationale:**
- Simple strategies don't have execution expertise
- Translator can use size/urgency to decide
- Allows gradual sophistication (start simple, add hints later)

**Example:**
```python
# Beginner strategy - no hints
ExecutionIntent(
    execution_urgency=Decimal("0.5"),
    # ... no hints - translator uses defaults
)

# Advanced strategy - with hints
ExecutionIntent(
    execution_urgency=Decimal("0.2"),
    preferred_execution_style="TWAP",  # Expert knowledge
    chunk_count_hint=10
)
```

---

### Decision 3: Why action field (not separate DTOs)?

**Problem:** Cancel/Modify operations need execution intent too

**Alternative Considered:**
- Separate `CancelIntent`, `ModifyIntent` DTOs

**Solution:** Single DTO with `action` enum

**Rationale:**
- All actions share urgency concept (cancel can be urgent!)
- Reduces DTO proliferation (1 DTO vs 4 DTOs)
- Simplifies translator interface (1 input type)

**Example:**
```python
# Same DTO structure for different actions
execute = ExecutionIntent(action=ExecutionAction.EXECUTE_TRADE, ...)
cancel = ExecutionIntent(action=ExecutionAction.CANCEL_ORDER, ...)
```

---

## 13. Next Steps (Implementation Plan)

### STAP 1: RED - Write Failing Tests
- Create `tests/unit/dtos/strategy/test_execution_intent.py`
- Write 15+ failing test cases
- Run pytest → ALL RED ✅

### STAP 2: GREEN - Implement DTO
- Create `backend/dtos/strategy/execution_intent.py`
- Implement all fields + validators
- Run pytest → ALL GREEN ✅

### STAP 3: REFACTOR - Quality & Examples
- Add `json_schema_extra` with 3+ examples
- Add comprehensive docstrings
- Run pylint → 10/10 ✅
- Update Quality Metrics Dashboard

---

**END OF CONCEPTUAL DESIGN**

**Status:** Ready for STAP 1 (RED - Write Failing Tests)  
**Sign-off:** Architecture Team ✅  
**Date:** 2025-10-28
