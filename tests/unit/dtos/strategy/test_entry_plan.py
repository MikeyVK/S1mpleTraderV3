"""
Unit tests for EntryPlan DTO.

Tests creation, validation, and edge cases for lean entry planning output.
EntryPlan represents WHAT/WHERE for entry (order specification only).
Timing/urgency/slippage belong in ExecutionPlan (HOW/WHEN).
"""
# pyright: reportCallIssue=false, reportAttributeAccessIssue=false
# Suppress Pydantic FieldInfo false positives for optional fields
# type: ignore[union-attr]

from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.dtos.strategy.entry_plan import EntryPlan


class TestEntryPlanCreation:
    """Test EntryPlan instantiation with lean spec."""

    def test_minimal_market_entry(self):
        """Can create minimal market entry plan."""
        plan = EntryPlan(
            symbol="BTCUSDT",
            direction="BUY",
            order_type="MARKET"
        )

        assert plan.symbol == "BTCUSDT"
        assert plan.direction == "BUY"
        assert plan.order_type == "MARKET"
        # Check plan_id prefix
        plan_id = str(plan.plan_id)
        assert plan_id.startswith("ENT_")
        assert plan.limit_price is None
        assert plan.stop_price is None

    def test_complete_limit_entry(self):
        """Can create complete limit entry plan."""
        plan = EntryPlan(
            symbol="ETHUSDT",
            direction="SELL",
            order_type="LIMIT",
            limit_price=Decimal("3510.00")
        )

        assert plan.symbol == "ETHUSDT"
        assert plan.direction == "SELL"
        assert plan.order_type == "LIMIT"
        assert plan.limit_price == Decimal("3510.00")
        assert plan.stop_price is None

    def test_stop_limit_entry(self):
        """Can create stop-limit entry plan."""
        plan = EntryPlan(
            symbol="SOLUSDT",
            direction="BUY",
            order_type="STOP_LIMIT",
            stop_price=Decimal("125.00"),
            limit_price=Decimal("125.50")
        )

        assert plan.order_type == "STOP_LIMIT"
        assert plan.stop_price == Decimal("125.00")
        assert plan.limit_price == Decimal("125.50")


class TestEntryPlanValidation:
    """Test EntryPlan validation rules."""

    def test_requires_symbol(self):
        """symbol is required."""
        with pytest.raises(ValidationError) as exc_info:
            EntryPlan(
                direction="BUY",
                order_type="MARKET"
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("symbol",) for e in errors)

    def test_requires_direction(self):
        """direction is required."""
        with pytest.raises(ValidationError) as exc_info:
            EntryPlan(
                symbol="BTCUSDT",
                order_type="MARKET"
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("direction",) for e in errors)

    def test_direction_must_be_buy_or_sell(self):
        """direction must be 'BUY' or 'SELL'."""
        with pytest.raises(ValidationError) as exc_info:
            EntryPlan(
                symbol="BTCUSDT",
                direction="HOLD",  # type: ignore[arg-type]  # Invalid direction
                order_type="MARKET"
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("direction",) for e in errors)

    def test_requires_order_type(self):
        """order_type is required."""
        with pytest.raises(ValidationError) as exc_info:
            EntryPlan(
                symbol="BTCUSDT",
                direction="BUY"
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("order_type",) for e in errors)

    def test_order_type_must_be_valid_literal(self):
        """order_type must be MARKET, LIMIT, or STOP_LIMIT."""
        with pytest.raises(ValidationError) as exc_info:
            EntryPlan(
                symbol="BTCUSDT",
                direction="BUY",
                order_type="TRAILING_STOP"  # type: ignore[arg-type]  # Invalid order type
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("order_type",) for e in errors)


class TestEntryPlanDefaultValues:
    """Test EntryPlan default value behavior."""

    def test_auto_generates_plan_id(self):
        """plan_id is auto-generated with ENT_ prefix."""
        plan1 = EntryPlan(
            symbol="BTCUSDT",
            direction="BUY",
            order_type="MARKET"
        )
        plan2 = EntryPlan(
            symbol="BTCUSDT",
            direction="BUY",
            order_type="MARKET"
        )

        # Check unique plan IDs
        plan1_id = str(plan1.plan_id)
        plan2_id = str(plan2.plan_id)
        assert plan1_id.startswith("ENT_")
        assert plan2_id.startswith("ENT_")
        assert plan1_id != plan2_id

    def test_optional_fields_default_to_none(self):
        """Optional fields default to None."""
        plan = EntryPlan(
            symbol="BTCUSDT",
            direction="BUY",
            order_type="MARKET"
        )

        assert plan.limit_price is None
        assert plan.stop_price is None


class TestEntryPlanSerialization:
    """Test EntryPlan serialization."""

    def test_can_serialize_to_dict(self):
        """Can serialize EntryPlan to dict."""
        plan = EntryPlan(
            symbol="BTCUSDT",
            direction="BUY",
            order_type="MARKET"
        )

        data = plan.model_dump()

        assert data["symbol"] == "BTCUSDT"
        assert data["direction"] == "BUY"
        assert data["order_type"] == "MARKET"
        assert "plan_id" in data
        assert data["plan_id"].startswith("ENT_")

    def test_can_serialize_to_json(self):
        """Can serialize EntryPlan to JSON."""
        plan = EntryPlan(
            symbol="BTCUSDT",
            direction="BUY",
            order_type="LIMIT",
            limit_price=Decimal("95000.00")
        )

        json_str = plan.model_dump_json()

        assert isinstance(json_str, str)
        assert "BTCUSDT" in json_str
        assert "BUY" in json_str
        assert "LIMIT" in json_str

    def test_can_deserialize_from_dict(self):
        """Can deserialize EntryPlan from dict."""
        data = {
            "plan_id": "ENT_20250125_120000_abc12345",
            "symbol": "BTCUSDT",
            "direction": "BUY",
            "order_type": "MARKET"
        }

        plan = EntryPlan.model_validate(data)

        assert plan.plan_id == "ENT_20250125_120000_abc12345"
        assert plan.symbol == "BTCUSDT"


class TestEntryPlanUseCases:
    """Test real-world EntryPlan use cases (lean spec)."""

    def test_immediate_market_order(self):
        """Immediate market entry (pure WHAT/WHERE)."""
        plan = EntryPlan(
            symbol="BTCUSDT",
            direction="BUY",
            order_type="MARKET"
        )

        assert plan.order_type == "MARKET"
        assert plan.limit_price is None
        # Note: Timing/urgency/slippage belong in ExecutionPlan

    def test_limit_entry_at_specific_price(self):
        """Limit entry at specific price level."""
        plan = EntryPlan(
            symbol="ETHUSDT",
            direction="BUY",
            order_type="LIMIT",
            limit_price=Decimal("3495.00")
        )

        assert plan.order_type == "LIMIT"
        assert plan.limit_price == Decimal("3495.00")
        # Note: Layering/TWAP params belong in ExecutionPlan

    def test_stop_limit_for_breakout(self):
        """Stop-limit entry for breakout scenario."""
        plan = EntryPlan(
            symbol="SOLUSDT",
            direction="BUY",
            order_type="STOP_LIMIT",
            stop_price=Decimal("125.00"),
            limit_price=Decimal("125.50")
        )

        assert plan.order_type == "STOP_LIMIT"
        assert plan.stop_price == Decimal("125.00")
        assert plan.limit_price == Decimal("125.50")
        # Note: Valid_until belongs in ExecutionPlan
