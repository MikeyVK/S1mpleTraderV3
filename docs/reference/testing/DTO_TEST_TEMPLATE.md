# DTO Test Template

## Overview

Copy-paste template for creating comprehensive tests for Strategy DTOs. Follow TDD workflow: write tests FIRST (RED phase), then implement DTO (GREEN phase).

## Test File Structure

### 1. File Header (REQUIRED)

```python
# tests/unit/dtos/strategy/test_{your_dto}.py
"""
Unit tests for {DTOName} DTO.

Tests the {purpose} contract according to TDD principles.
{Brief explanation of what this DTO represents}

@layer: Tests (Unit)
@dependencies: [pytest, pydantic, backend.dtos.strategy.{your_dto}]
"""
# pyright: reportCallIssue=false, reportAttributeAccessIssue=false
# Suppress Pydantic FieldInfo false positives for optional fields
```

**Why pyright comments:**
- Pylance doesn't recognize Pydantic field resolution at runtime
- `signal.field_name` triggers "FieldInfo has no member" warnings
- Runtime works perfectly - this is Pylance limitation only

### 2. Imports (3 Groups with Comments)

```python
# Standard library
from datetime import datetime, timezone
from decimal import Decimal
from typing import cast

# Third-party
import pytest
from pydantic import ValidationError

# Project modules
from backend.dtos.strategy.{your_dto} import {DTOName}
from backend.dtos.causality import CausalityChain  # If DTO has causality
from backend.utils.id_generators import (
    generate_tick_id,
    generate_{your_dto}_id
)
```

## Test Suite Organization

Organize tests into **logical test classes** by functionality:

### Test Class Template

```python
class Test{DTOName}{Aspect}:
    """Test suite for {aspect} of {DTOName}."""

    def test_{scenario}_succeeds(self):
        """Test that {scenario} works correctly."""
        # Arrange
        dto = {DTOName}(
            causality=CausalityChain(tick_id=generate_tick_id()),
            field1="value1",
            field2=Decimal("123.45")
        )

        # Act & Assert
        assert dto.field1 == "value1"
        assert dto.field2 == Decimal("123.45")

    def test_{scenario}_fails(self):
        """Test that {scenario} is rejected."""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            {DTOName}(
                causality=CausalityChain(tick_id=generate_tick_id()),
                field1="invalid_value"
            )

        # Verify error message
        assert "field1" in str(exc_info.value)
```

## Standard Test Suites

Every DTO should have these test classes (20-30 tests typical):

### 1. Creation Tests (3-5 tests)

```python
class Test{DTOName}Creation:
    """Test suite for {DTOName} instantiation."""

    def test_create_minimal_{dto}(self):
        """Test creating {dto} with required fields only."""
        dto = {DTOName}(
            causality=CausalityChain(tick_id=generate_tick_id()),  # If applicable
            timestamp=datetime.now(timezone.utc),
            field1="value1",
            field2="value2"
        )

        # Verify causality (if applicable)
        causality = cast(CausalityChain, dto.causality)
        assert getattr(causality, "tick_id") is not None
        assert getattr(causality, "tick_id").startswith("TCK_")

        # Verify fields
        assert dto.field1 == "value1"
        assert dto.field2 == "value2"

    def test_create_{dto}_with_optional_fields(self):
        """Test creating {dto} with optional fields."""
        dto = {DTOName}(
            causality=CausalityChain(tick_id=generate_tick_id()),
            field1="value1",
            optional_field=Decimal("99.99")
        )

        assert dto.optional_field == Decimal("99.99")

    def test_{dto}_id_auto_generated(self):
        """Test that {dto}_id is auto-generated if not provided."""
        dto = {DTOName}(
            causality=CausalityChain(tick_id=generate_tick_id()),
            field1="value1"
        )

        # Use str() to avoid Pylance FieldInfo warnings
        dto_id = str(dto.{dto}_id)
        assert dto_id.startswith("{PREFIX}_")

    def test_custom_{dto}_id_accepted(self):
        """Test that custom {dto}_id can be provided."""
        custom_id = generate_{dto}_id()
        dto = {DTOName}(
            causality=CausalityChain(tick_id=generate_tick_id()),
            {dto}_id=custom_id,
            field1="value1"
        )

        assert dto.{dto}_id == custom_id
```

**Workaround for Pylance FieldInfo warnings:**

Use **`getattr()`** to access Pydantic fields in assertions:

```python
# ✅ PREFERRED - Use getattr()
assert getattr(signal, "initiator_id").startswith("TCK_")

# ✅ ACCEPTABLE - Intermediate variable (legacy pattern)
initiator_id = str(signal.initiator_id)
assert initiator_id.startswith("TCK_")

# ❌ TRIGGERS WARNING - Direct access
assert signal.initiator_id.startswith("TCK_")  # Pylance: no member 'startswith'
```

**For complex nested attributes:**

```python
from typing import cast
from datetime import datetime

# Datetime attributes need casting + getattr
dt = cast(datetime, directive.decision_timestamp)
assert getattr(dt, "tzinfo") is not None
```

### 2. ID Validation Tests (2-3 tests)

```python
class Test{DTOName}IDValidation:
    """Test suite for {dto}_id validation."""

    def test_valid_{dto}_id_format(self):
        """Test that {PREFIX}_ prefix with military datetime is valid."""
        dto = {DTOName}(
            causality=CausalityChain(tick_id=generate_tick_id()),
            {dto}_id=generate_{dto}_id(),
            field1="value1"
        )

        dto_id = str(dto.{dto}_id)
        assert dto_id.startswith("{PREFIX}_")

    def test_invalid_{dto}_id_prefix_rejected(self):
        """Test that non-{PREFIX}_ prefix is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            {DTOName}(
                causality=CausalityChain(tick_id=generate_tick_id()),
                {dto}_id="WRONG_20251027_100000_a1b2c3d4",
                field1="value1"
            )

        assert "{dto}_id" in str(exc_info.value)

    def test_invalid_{dto}_id_format_rejected(self):
        """Test that malformed ID format is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            {DTOName}(
                causality=CausalityChain(tick_id=generate_tick_id()),
                {dto}_id="{PREFIX}_invalid_format",
                field1="value1"
            )

        assert "must match format" in str(exc_info.value).lower()
```

### 3. Timestamp Validation Tests (3 tests, if applicable)

```python
class Test{DTOName}TimestampValidation:
    """Test suite for timestamp validation."""

    def test_naive_datetime_converted_to_utc(self):
        """Test that naive datetime is assumed to be UTC."""
        naive_dt = datetime(2025, 1, 15, 10, 30, 0)
        dto = {DTOName}(
            causality=CausalityChain(tick_id=generate_tick_id()),
            timestamp=naive_dt,
            field1="value1"
        )

        # Verify conversion
        assert naive_dt.year == 2025
        assert dto.timestamp == naive_dt.replace(tzinfo=timezone.utc)

    def test_aware_datetime_preserved(self):
        """Test that timezone-aware datetime is preserved."""
        aware_dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        dto = {DTOName}(
            causality=CausalityChain(tick_id=generate_tick_id()),
            timestamp=aware_dt,
            field1="value1"
        )

        assert dto.timestamp == aware_dt
        assert getattr(dto.timestamp, "tzinfo") == timezone.utc

    def test_non_utc_datetime_converted(self):
        """Test that non-UTC timezone is converted to UTC."""
        # Create non-UTC timezone
        from datetime import timedelta
        eastern = timezone(timedelta(hours=-5))
        eastern_dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=eastern)

        dto = {DTOName}(
            causality=CausalityChain(tick_id=generate_tick_id()),
            timestamp=eastern_dt,
            field1="value1"
        )

        # Should be converted to UTC
        assert getattr(dto.timestamp, "tzinfo") == timezone.utc
        # Time should be adjusted (10:30 EST = 15:30 UTC)
        assert dto.timestamp.hour == 15
```

### 4. Field Validation Tests (4-8 tests)

```python
class Test{DTOName}{FieldName}Validation:
    """Test suite for {field_name} validation."""

    def test_valid_{field}_accepted(self):
        """Test that valid {field} value is accepted."""
        dto = {DTOName}(
            causality=CausalityChain(tick_id=generate_tick_id()),
            {field}="VALID_VALUE"
        )

        assert dto.{field} == "VALID_VALUE"

    def test_invalid_{field}_rejected(self):
        """Test that invalid {field} value is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            {DTOName}(
                causality=CausalityChain(tick_id=generate_tick_id()),
                {field}="invalid value"
            )

        assert "{field}" in str(exc_info.value)

    def test_{field}_min_length_enforced(self):
        """Test that minimum length is enforced."""
        with pytest.raises(ValidationError) as exc_info:
            {DTOName}(
                causality=CausalityChain(tick_id=generate_tick_id()),
                {field}="AB"  # Too short
            )

        assert "at least" in str(exc_info.value).lower()

    def test_{field}_max_length_enforced(self):
        """Test that maximum length is enforced."""
        with pytest.raises(ValidationError) as exc_info:
            {DTOName}(
                causality=CausalityChain(tick_id=generate_tick_id()),
                {field}="A" * 100  # Too long
            )

        assert "at most" in str(exc_info.value).lower()
```

**Common validation patterns:**

**String length:**
```python
def test_field_min_length(self):
    with pytest.raises(ValidationError):
        MyDTO(field="AB")  # min_length=3

def test_field_max_length(self):
    with pytest.raises(ValidationError):
        MyDTO(field="A" * 100)  # max_length=50
```

**Regex pattern:**
```python
def test_asset_format_valid(self):
    dto = MyDTO(asset="BTC/USDT")
    assert dto.asset == "BTC/USDT"

def test_asset_format_invalid(self):
    with pytest.raises(ValidationError):
        MyDTO(asset="invalid_format")
```

**Decimal ranges:**
```python
def test_confidence_range_valid(self):
    dto = MyDTO(confidence=0.85)
    assert dto.confidence == 0.85

def test_confidence_below_min_rejected(self):
    with pytest.raises(ValidationError):
        MyDTO(confidence=-0.1)  # ge=0.0

def test_confidence_above_max_rejected(self):
    with pytest.raises(ValidationError):
        MyDTO(confidence=1.1)  # le=1.0
```

**Literal values:**
```python
def test_direction_long_valid(self):
    dto = MyDTO(direction="long")
    assert dto.direction == "long"

def test_direction_short_valid(self):
    dto = MyDTO(direction="short")
    assert dto.direction == "short"

def test_invalid_direction_rejected(self):
    with pytest.raises(ValidationError):
        MyDTO(direction="sideways")
```

### 5. Immutability Tests (2 tests, if frozen=True)

```python
class Test{DTOName}Immutability:
    """Test suite for {DTOName} immutability."""

    def test_{dto}_is_frozen(self):
        """Test that {dto} fields cannot be modified after creation."""
        dto = {DTOName}(
            causality=CausalityChain(tick_id=generate_tick_id()),
            field1="original"
        )

        with pytest.raises(ValidationError) as exc_info:
            dto.field1 = "modified"

        assert "frozen" in str(exc_info.value).lower()

    def test_{dto}_no_extra_fields(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError) as exc_info:
            {DTOName}(
                causality=CausalityChain(tick_id=generate_tick_id()),
                field1="value1",
                extra_field="not_allowed"
            )

        assert "extra" in str(exc_info.value).lower()
```

### 6. Cross-Field Validation Tests (if applicable)

```python
class Test{DTOName}CrossFieldValidation:
    """Test suite for cross-field validation rules."""

    def test_limit_price_required_for_limit_orders(self):
        """Test that LIMIT orders must have limit_price."""
        with pytest.raises(ValidationError) as exc_info:
            EntryPlan(
                symbol="BTCUSDT",
                direction="BUY",
                order_type="LIMIT"
                # Missing limit_price
            )

        assert "limit_price" in str(exc_info.value)

    def test_stop_limit_requires_both_prices(self):
        """Test that STOP_LIMIT requires both stop_price and limit_price."""
        with pytest.raises(ValidationError) as exc_info:
            EntryPlan(
                symbol="BTCUSDT",
                direction="BUY",
                order_type="STOP_LIMIT",
                stop_price=Decimal("100.00")
                # Missing limit_price
            )

        assert "limit_price" in str(exc_info.value)

    def test_market_order_ignores_prices(self):
        """Test that MARKET orders don't need price fields."""
        plan = EntryPlan(
            symbol="BTCUSDT",
            direction="BUY",
            order_type="MARKET"
        )

        assert plan.limit_price is None
        assert plan.stop_price is None
```

### 7. Edge Cases & Integration Tests (2-4 tests)

```python
class Test{DTOName}EdgeCases:
    """Test suite for edge cases and integration scenarios."""

    def test_all_optional_fields_none(self):
        """Test creating {dto} with all optional fields as None."""
        dto = {DTOName}(
            causality=CausalityChain(tick_id=generate_tick_id()),
            required_field="value"
            # All optional fields omitted
        )

        assert dto.optional_field1 is None
        assert dto.optional_field2 is None

    def test_round_trip_serialization(self):
        """Test that {dto} can be serialized and deserialized."""
        original = {DTOName}(
            causality=CausalityChain(tick_id=generate_tick_id()),
            field1="value1",
            field2=Decimal("123.45")
        )

        # Serialize to dict
        dto_dict = original.model_dump()

        # Deserialize from dict
        restored = {DTOName}(**dto_dict)

        assert restored.field1 == original.field1
        assert restored.field2 == original.field2

    def test_json_schema_examples_are_valid(self):
        """Test that all json_schema_extra examples are valid."""
        from backend.dtos.strategy.{your_dto} import {DTOName}

        examples = {DTOName}.model_config["json_schema_extra"]["examples"]

        for example in examples:
            # Remove description field (not part of DTO)
            example_copy = example.copy()
            example_copy.pop("description", None)

            # Should not raise ValidationError
            dto = {DTOName}(**example_copy)
            assert dto is not None
```

## Quality Checklist

Before committing tests (RED phase):

- [ ] File header with @layer and @dependencies
- [ ] pyright suppressions for Pydantic FieldInfo warnings
- [ ] Imports in 3 groups (Standard, Third-party, Project)
- [ ] Test classes organized by aspect (Creation, Validation, etc.)
- [ ] 20-30 tests covering all validation rules
- [ ] Tests use `getattr()` for Pydantic field access
- [ ] Tests for ID format (military datetime pattern)
- [ ] Tests for timestamp UTC conversion (if applicable)
- [ ] Tests for all field validators (length, pattern, range)
- [ ] Tests for immutability (if frozen=True)
- [ ] Tests for cross-field validation (if applicable)
- [ ] Tests for json_schema_extra examples validity
- [ ] All tests FAIL (RED phase - implementation not done yet)

## TDD Workflow Integration

**RED Phase:**
```powershell
# Write all tests first (this template)
# Run tests - should all fail
pytest tests/unit/dtos/strategy/test_{your_dto}.py -v

# Commit failing tests
git add tests/unit/dtos/strategy/test_{your_dto}.py
git commit -m "test: add failing tests for {DTOName} DTO

- Creation tests (4)
- ID validation tests (3)
- Timestamp validation tests (3)
- Field validation tests (8)
- Immutability tests (2)
- Edge cases (3)

Status: RED - tests fail (23/23)"
```

**GREEN Phase:**
```powershell
# Implement DTO to make tests pass
# Run tests - should all pass
pytest tests/unit/dtos/strategy/test_{your_dto}.py -v

# Commit implementation
git add backend/dtos/strategy/{your_dto}.py
git commit -m "feat: implement {DTOName} DTO

- Add all required fields
- Add validators for ID, timestamp, fields
- All tests passing (23/23)

Status: GREEN"
```

**REFACTOR Phase:**
```powershell
# Improve code quality
# - Add json_schema_extra examples
# - Fix trailing whitespace
# - Enhance docstrings

# Run tests - should still pass
pytest tests/unit/dtos/strategy/test_{your_dto}.py -v

# Commit refactoring
git add backend/dtos/strategy/{your_dto}.py tests/unit/dtos/strategy/test_{your_dto}.py
git commit -m "refactor: improve {DTOName} quality

- Add json_schema_extra examples (3)
- Fix trailing whitespace
- Enhance docstrings

Quality gates: 10/10
Status: GREEN (tests still 23/23)"
```

## Related Documentation

- [STRATEGY_DTO_TEMPLATE.md](../dtos/STRATEGY_DTO_TEMPLATE.md) - DTO template
- [../../coding_standards/TDD_WORKFLOW.md](../../coding_standards/TDD_WORKFLOW.md) - TDD workflow
- [../../coding_standards/QUALITY_GATES.md](../../coding_standards/QUALITY_GATES.md) - Quality gates
- [opportunity_signal.md](../platform/opportunity_signal.md) - Reference example tests
