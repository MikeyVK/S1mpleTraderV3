# tests/unit/dtos/state/test_fill.py
"""
Unit tests for Fill DTO.

Tests the Fill data structure used to track exchange execution events.
Following TDD workflow - these tests define the expected behavior.

@layer: Tests
@tests: backend/dtos/state/fill.py
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.dtos.state.fill import Fill


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def valid_fill_data() -> dict:
    """Provide valid Fill data for testing."""
    return {
        "parent_order_id": "ORD_20251201_150100_b2c3d4e5",
        "connector_fill_id": "binance_fill_987654321",
        "filled_quantity": Decimal("2.0"),
        "fill_price": Decimal("3450.25"),
        "commission": Decimal("0.003"),
        "commission_asset": "BNB",
        "executed_at": datetime.now(timezone.utc),
    }


@pytest.fixture
def minimal_fill_data() -> dict:
    """Provide minimal Fill data (only required fields)."""
    return {
        "parent_order_id": "ORD_20251201_150100_b2c3d4e5",
        "filled_quantity": Decimal("2.0"),
        "fill_price": Decimal("3450.25"),
        "executed_at": datetime.now(timezone.utc),
    }


# =============================================================================
# FILL CREATION TESTS
# =============================================================================


class TestFillCreation:
    """Tests for Fill instantiation."""

    def test_create_with_required_fields(
        self, minimal_fill_data: dict
    ) -> None:
        """Should create Fill with required fields only."""
        fill = Fill(**minimal_fill_data)

        assert fill.fill_id.startswith("FIL_")
        assert fill.parent_order_id == "ORD_20251201_150100_b2c3d4e5"
        assert fill.filled_quantity == Decimal("2.0")
        assert fill.fill_price == Decimal("3450.25")
        assert fill.connector_fill_id is None
        assert fill.commission is None
        assert fill.commission_asset is None

    def test_create_with_all_fields(
        self, valid_fill_data: dict
    ) -> None:
        """Should create Fill with all fields."""
        fill = Fill(**valid_fill_data)

        assert fill.fill_id.startswith("FIL_")
        assert fill.parent_order_id == "ORD_20251201_150100_b2c3d4e5"
        assert fill.connector_fill_id == "binance_fill_987654321"
        assert fill.filled_quantity == Decimal("2.0")
        assert fill.fill_price == Decimal("3450.25")
        assert fill.commission == Decimal("0.003")
        assert fill.commission_asset == "BNB"

    def test_auto_generates_fill_id_with_correct_prefix(
        self, minimal_fill_data: dict
    ) -> None:
        """Should auto-generate ID with FIL_ prefix."""
        fill = Fill(**minimal_fill_data)
        assert fill.fill_id.startswith("FIL_")
        # Format: FIL_YYYYMMDD_HHMMSS_hash
        parts = fill.fill_id.split("_")
        assert len(parts) == 4
        assert parts[0] == "FIL"


# =============================================================================
# FILL VALIDATION TESTS
# =============================================================================


class TestFillValidation:
    """Tests for Fill field validation."""

    def test_rejects_invalid_parent_order_id_prefix(
        self, minimal_fill_data: dict
    ) -> None:
        """Should reject parent_order_id without ORD_ prefix."""
        minimal_fill_data["parent_order_id"] = "INVALID_20251201_150100_xyz"
        with pytest.raises(ValidationError) as exc_info:
            Fill(**minimal_fill_data)
        assert "parent_order_id" in str(exc_info.value)

    def test_rejects_zero_filled_quantity(
        self, minimal_fill_data: dict
    ) -> None:
        """Should reject filled_quantity <= 0."""
        minimal_fill_data["filled_quantity"] = Decimal("0")
        with pytest.raises(ValidationError) as exc_info:
            Fill(**minimal_fill_data)
        assert "filled_quantity" in str(exc_info.value)

    def test_rejects_negative_filled_quantity(
        self, minimal_fill_data: dict
    ) -> None:
        """Should reject negative filled_quantity."""
        minimal_fill_data["filled_quantity"] = Decimal("-0.5")
        with pytest.raises(ValidationError) as exc_info:
            Fill(**minimal_fill_data)
        assert "filled_quantity" in str(exc_info.value)

    def test_rejects_zero_fill_price(
        self, minimal_fill_data: dict
    ) -> None:
        """Should reject fill_price <= 0."""
        minimal_fill_data["fill_price"] = Decimal("0")
        with pytest.raises(ValidationError) as exc_info:
            Fill(**minimal_fill_data)
        assert "fill_price" in str(exc_info.value)

    def test_rejects_negative_fill_price(
        self, minimal_fill_data: dict
    ) -> None:
        """Should reject negative fill_price."""
        minimal_fill_data["fill_price"] = Decimal("-100.00")
        with pytest.raises(ValidationError) as exc_info:
            Fill(**minimal_fill_data)
        assert "fill_price" in str(exc_info.value)

    def test_rejects_negative_commission(
        self, valid_fill_data: dict
    ) -> None:
        """Should reject commission < 0."""
        valid_fill_data["commission"] = Decimal("-0.001")
        with pytest.raises(ValidationError) as exc_info:
            Fill(**valid_fill_data)
        assert "commission" in str(exc_info.value)

    def test_accepts_zero_commission(
        self, valid_fill_data: dict
    ) -> None:
        """Should accept commission = 0 (maker rebates possible)."""
        valid_fill_data["commission"] = Decimal("0")
        fill = Fill(**valid_fill_data)
        assert fill.commission == Decimal("0")


# =============================================================================
# FILL IMMUTABILITY TESTS
# =============================================================================


class TestFillImmutability:
    """Tests for Fill immutability (frozen=True)."""

    def test_cannot_modify_fill_price(
        self, valid_fill_data: dict
    ) -> None:
        """Should raise error when modifying fill_price."""
        fill = Fill(**valid_fill_data)
        with pytest.raises(ValidationError):
            fill.fill_price = Decimal("9999.99")

    def test_cannot_modify_filled_quantity(
        self, valid_fill_data: dict
    ) -> None:
        """Should raise error when modifying filled_quantity."""
        fill = Fill(**valid_fill_data)
        with pytest.raises(ValidationError):
            fill.filled_quantity = Decimal("999.0")

    def test_cannot_modify_fill_id(
        self, valid_fill_data: dict
    ) -> None:
        """Should raise error when modifying fill_id."""
        fill = Fill(**valid_fill_data)
        with pytest.raises(ValidationError):
            fill.fill_id = "FIL_FAKE_ID_12345678"

    def test_cannot_modify_executed_at(
        self, valid_fill_data: dict
    ) -> None:
        """Should raise error when modifying executed_at."""
        fill = Fill(**valid_fill_data)
        with pytest.raises(ValidationError):
            fill.executed_at = datetime.now(timezone.utc)


# =============================================================================
# FILL EXAMPLES TESTS
# =============================================================================


class TestFillExamples:
    """Tests for Fill json_schema_extra examples."""

    def test_has_json_schema_examples(self) -> None:
        """Should have json_schema_extra examples defined."""
        schema = Fill.model_json_schema()
        assert "examples" in schema

    def test_examples_are_valid(self) -> None:
        """All examples in json_schema_extra should be valid."""
        schema = Fill.model_json_schema()
        examples = schema.get("examples", [])
        assert len(examples) >= 1

        for example in examples:
            # Remove description field if present (not part of model)
            example_data = {k: v for k, v in example.items() if k != "description"}
            # This should not raise
            Fill.model_validate(example_data)


# =============================================================================
# FILL VALUE CALCULATION TESTS
# =============================================================================


class TestFillValueCalculation:
    """Tests for computed values based on Fill data."""

    def test_fill_value_can_be_computed(
        self, valid_fill_data: dict
    ) -> None:
        """Should be able to compute fill value (qty * price)."""
        fill = Fill(**valid_fill_data)
        fill_value = fill.filled_quantity * fill.fill_price
        assert fill_value == Decimal("6900.50")  # 2.0 * 3450.25

    def test_multiple_fills_same_order_different_prices(
        self, minimal_fill_data: dict
    ) -> None:
        """Multiple fills for same order can have different prices."""
        fill1 = Fill(**minimal_fill_data)
        minimal_fill_data["fill_price"] = Decimal("3451.00")
        fill2 = Fill(**minimal_fill_data)

        # Both should be valid with same parent
        assert fill1.parent_order_id == fill2.parent_order_id
        assert fill1.fill_price != fill2.fill_price
        # But different fill_ids
        assert fill1.fill_id != fill2.fill_id

