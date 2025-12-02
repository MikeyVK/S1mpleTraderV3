# tests/unit/dtos/state/test_order.py
"""
Unit tests for Order DTO.

Tests the Order data structure used to track exchange order lifecycle.
Following TDD workflow - these tests define the expected behavior.

@layer: Tests
@tests: backend/dtos/state/order.py
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.core.enums import OrderStatus, OrderType
from backend.dtos.state.order import Order


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def valid_order_data() -> dict:
    """Provide valid Order data for testing."""
    return {
        "parent_group_id": "EXG_20251201_145955_xyz789",
        "symbol": "BTC_USDT",
        "side": "BUY",
        "order_type": OrderType.LIMIT,
        "quantity": Decimal("0.5"),
        "price": Decimal("95000.00"),
        "status": OrderStatus.PENDING,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


@pytest.fixture
def market_order_data() -> dict:
    """Provide valid Market Order data for testing."""
    return {
        "parent_group_id": "EXG_20251201_150055_abc123",
        "symbol": "ETH_USDT",
        "side": "SELL",
        "order_type": OrderType.MARKET,
        "quantity": Decimal("2.0"),
        "status": OrderStatus.PENDING,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


# =============================================================================
# ORDER CREATION TESTS
# =============================================================================


class TestOrderCreation:
    """Tests for Order instantiation."""

    def test_create_limit_order_with_required_fields(
        self, valid_order_data: dict
    ) -> None:
        """Should create limit Order with required fields."""
        order = Order(**valid_order_data)

        assert getattr(order, "order_id").startswith("ORD_")
        assert order.parent_group_id == "EXG_20251201_145955_xyz789"
        assert order.symbol == "BTC_USDT"
        assert order.side == "BUY"
        assert order.order_type == OrderType.LIMIT
        assert order.quantity == Decimal("0.5")
        assert order.price == Decimal("95000.00")
        assert order.status == OrderStatus.PENDING

    def test_create_market_order_without_price(
        self, market_order_data: dict
    ) -> None:
        """Should create market Order without price."""
        order = Order(**market_order_data)

        assert order.order_type == OrderType.MARKET
        assert order.price is None
        assert order.stop_price is None

    def test_auto_generates_order_id_with_correct_prefix(
        self, valid_order_data: dict
    ) -> None:
        """Should auto-generate ID with ORD_ prefix."""
        order = Order(**valid_order_data)
        order_id = getattr(order, "order_id")
        assert order_id.startswith("ORD_")
        # Format: ORD_YYYYMMDD_HHMMSS_hash
        parts = order_id.split("_")
        assert len(parts) == 4
        assert parts[0] == "ORD"

    def test_connector_order_id_defaults_to_none(
        self, valid_order_data: dict
    ) -> None:
        """Should default connector_order_id to None."""
        order = Order(**valid_order_data)
        assert order.connector_order_id is None

    def test_can_set_connector_order_id(
        self, valid_order_data: dict
    ) -> None:
        """Should accept connector_order_id from exchange."""
        valid_order_data["connector_order_id"] = "binance_12345678"
        order = Order(**valid_order_data)
        assert order.connector_order_id == "binance_12345678"


# =============================================================================
# ORDER VALIDATION TESTS
# =============================================================================


class TestOrderValidation:
    """Tests for Order field validation."""

    def test_rejects_invalid_parent_group_id_prefix(
        self, valid_order_data: dict
    ) -> None:
        """Should reject parent_group_id without EXG_ prefix."""
        valid_order_data["parent_group_id"] = "INVALID_20251201_145955_xyz789"
        with pytest.raises(ValidationError) as exc_info:
            Order(**valid_order_data)
        assert "parent_group_id" in str(exc_info.value)

    def test_rejects_invalid_symbol_format(
        self, valid_order_data: dict
    ) -> None:
        """Should reject invalid symbol format."""
        valid_order_data["symbol"] = "btc-usdt"  # lowercase, wrong separator
        with pytest.raises(ValidationError) as exc_info:
            Order(**valid_order_data)
        assert "symbol" in str(exc_info.value)

    def test_rejects_invalid_side(
        self, valid_order_data: dict
    ) -> None:
        """Should reject invalid side value."""
        valid_order_data["side"] = "LONG"  # Not BUY/SELL
        with pytest.raises(ValidationError) as exc_info:
            Order(**valid_order_data)
        assert "side" in str(exc_info.value)

    def test_rejects_zero_quantity(
        self, valid_order_data: dict
    ) -> None:
        """Should reject quantity <= 0."""
        valid_order_data["quantity"] = Decimal("0")
        with pytest.raises(ValidationError) as exc_info:
            Order(**valid_order_data)
        assert "quantity" in str(exc_info.value)

    def test_rejects_negative_quantity(
        self, valid_order_data: dict
    ) -> None:
        """Should reject negative quantity."""
        valid_order_data["quantity"] = Decimal("-0.5")
        with pytest.raises(ValidationError) as exc_info:
            Order(**valid_order_data)
        assert "quantity" in str(exc_info.value)

    def test_limit_order_requires_price(
        self, valid_order_data: dict
    ) -> None:
        """Should require price for LIMIT orders."""
        valid_order_data["order_type"] = OrderType.LIMIT
        valid_order_data["price"] = None
        with pytest.raises(ValidationError) as exc_info:
            Order(**valid_order_data)
        assert "price" in str(exc_info.value).lower()

    def test_stop_limit_order_requires_stop_price(
        self, valid_order_data: dict
    ) -> None:
        """Should require stop_price for STOP_LIMIT orders."""
        valid_order_data["order_type"] = OrderType.STOP_LIMIT
        valid_order_data["stop_price"] = None
        with pytest.raises(ValidationError) as exc_info:
            Order(**valid_order_data)
        assert "stop_price" in str(exc_info.value).lower()

    def test_market_order_ignores_price(
        self, market_order_data: dict
    ) -> None:
        """Should allow market orders without price."""
        order = Order(**market_order_data)
        assert order.price is None


# =============================================================================
# ORDER MUTABILITY TESTS
# =============================================================================


class TestOrderMutability:
    """Tests for Order mutability (frozen=False)."""

    def test_can_update_status(
        self, valid_order_data: dict
    ) -> None:
        """Should allow status updates (mutable)."""
        order = Order(**valid_order_data)
        order.status = OrderStatus.FILLED
        assert order.status == OrderStatus.FILLED

    def test_can_update_connector_order_id(
        self, valid_order_data: dict
    ) -> None:
        """Should allow connector_order_id updates."""
        order = Order(**valid_order_data)
        order.connector_order_id = "exchange_order_123"
        assert order.connector_order_id == "exchange_order_123"

    def test_can_update_updated_at(
        self, valid_order_data: dict
    ) -> None:
        """Should allow updated_at timestamp changes."""
        order = Order(**valid_order_data)
        new_time = datetime.now(timezone.utc)
        order.updated_at = new_time
        assert order.updated_at == new_time

    def test_order_id_is_effectively_immutable(
        self, valid_order_data: dict
    ) -> None:
        """order_id should not change after creation (by convention)."""
        order = Order(**valid_order_data)
        original_id = order.order_id
        # Even though frozen=False, IDs shouldn't be changed
        # This test documents the convention
        assert order.order_id == original_id


# =============================================================================
# ORDER STATUS TRANSITION TESTS
# =============================================================================


class TestOrderStatusTransitions:
    """Tests for Order status transitions."""

    def test_pending_to_open(
        self, valid_order_data: dict
    ) -> None:
        """Should allow PENDING → OPEN transition."""
        order = Order(**valid_order_data)
        assert order.status == OrderStatus.PENDING
        order.status = OrderStatus.OPEN
        assert order.status == OrderStatus.OPEN

    def test_open_to_filled(
        self, valid_order_data: dict
    ) -> None:
        """Should allow OPEN → FILLED transition."""
        valid_order_data["status"] = OrderStatus.OPEN
        order = Order(**valid_order_data)
        order.status = OrderStatus.FILLED
        assert order.status == OrderStatus.FILLED

    def test_open_to_partially_filled(
        self, valid_order_data: dict
    ) -> None:
        """Should allow OPEN → PARTIALLY_FILLED transition."""
        valid_order_data["status"] = OrderStatus.OPEN
        order = Order(**valid_order_data)
        order.status = OrderStatus.PARTIALLY_FILLED
        assert order.status == OrderStatus.PARTIALLY_FILLED

    def test_open_to_cancelled(
        self, valid_order_data: dict
    ) -> None:
        """Should allow OPEN → CANCELLED transition."""
        valid_order_data["status"] = OrderStatus.OPEN
        order = Order(**valid_order_data)
        order.status = OrderStatus.CANCELLED
        assert order.status == OrderStatus.CANCELLED


# =============================================================================
# ORDER EXAMPLES TESTS
# =============================================================================


class TestOrderExamples:
    """Tests for Order json_schema_extra examples."""

    def test_has_json_schema_examples(self) -> None:
        """Should have json_schema_extra examples defined."""
        schema = Order.model_json_schema()
        assert "examples" in schema

    def test_examples_are_valid(self) -> None:
        """All examples in json_schema_extra should be valid."""
        schema = Order.model_json_schema()
        examples = schema.get("examples", [])
        assert len(examples) >= 1

        for example in examples:
            # Remove description field if present (not part of model)
            example_data = {k: v for k, v in example.items() if k != "description"}
            # This should not raise
            Order.model_validate(example_data)

