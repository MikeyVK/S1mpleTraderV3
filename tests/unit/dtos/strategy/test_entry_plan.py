"""
Unit tests for EntryPlan DTO.

Tests creation, validation, and edge cases for entry planning output.
"""
# pyright: reportCallIssue=false
# Suppress Pydantic FieldInfo false positives for optional fields
# type: ignore[union-attr]

from datetime import datetime, timezone, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.dtos.strategy.entry_plan import EntryPlan


class TestEntryPlanCreation:
    """Test EntryPlan instantiation."""

    def test_minimal_market_entry(self):
        """Can create minimal market entry plan."""
        plan = EntryPlan(
            planner_id="test_planner",
            symbol="BTCUSDT",
            direction="BUY",
            order_type="MARKET",
            timing="IMMEDIATE",
            rationale="Test entry"
        )

        assert plan.planner_id == "test_planner"
        assert plan.symbol == "BTCUSDT"
        assert plan.direction == "BUY"
        assert plan.order_type == "MARKET"
        assert plan.timing == "IMMEDIATE"
        # Check plan_id prefix
        plan_id = str(plan.plan_id)
        assert plan_id.startswith("ENT_")
        assert isinstance(plan.created_at, datetime)
        assert plan.reference_price is None
        assert plan.limit_price is None

    def test_complete_limit_entry(self):
        """Can create complete limit entry plan."""
        now = datetime.now(timezone.utc)
        valid_until = now + timedelta(minutes=30)

        plan = EntryPlan(
            planner_id="layered_entry",
            symbol="ETHUSDT",
            direction="SELL",
            order_type="LIMIT",
            timing="LAYERED",
            reference_price=Decimal("3500.00"),
            limit_price=Decimal("3510.00"),
            max_slippage_pct=Decimal("0.002"),
            valid_until=valid_until,
            planner_metadata={"layers": 3},
            rationale="Layered entry for large position"
        )

        assert plan.symbol == "ETHUSDT"
        assert plan.direction == "SELL"
        assert plan.order_type == "LIMIT"
        assert plan.limit_price == Decimal("3510.00")
        assert plan.max_slippage_pct == Decimal("0.002")
        assert plan.valid_until == valid_until
        assert plan.planner_metadata == {"layers": 3}

    def test_stop_limit_entry(self):
        """Can create stop-limit entry plan."""
        plan = EntryPlan(
            planner_id="breakout_entry",
            symbol="SOLUSDT",
            direction="BUY",
            order_type="STOP_LIMIT",
            timing="PATIENT",
            stop_price=Decimal("125.00"),
            limit_price=Decimal("125.50"),
            rationale="Breakout entry above resistance"
        )

        assert plan.order_type == "STOP_LIMIT"
        assert plan.stop_price == Decimal("125.00")
        assert plan.limit_price == Decimal("125.50")


class TestEntryPlanValidation:
    """Test EntryPlan validation rules."""

    def test_requires_planner_id(self):
        """planner_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            EntryPlan(
                symbol="BTCUSDT",
                direction="BUY",
                order_type="MARKET",
                timing="IMMEDIATE",
                rationale="Test"
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("planner_id",) for e in errors)

    def test_requires_symbol(self):
        """symbol is required."""
        with pytest.raises(ValidationError) as exc_info:
            EntryPlan(
                planner_id="test",
                direction="BUY",
                order_type="MARKET",
                timing="IMMEDIATE",
                rationale="Test"
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("symbol",) for e in errors)

    def test_requires_direction(self):
        """direction is required."""
        with pytest.raises(ValidationError) as exc_info:
            EntryPlan(
                planner_id="test",
                symbol="BTCUSDT",
                order_type="MARKET",
                timing="IMMEDIATE",
                rationale="Test"
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("direction",) for e in errors)

    def test_direction_must_be_buy_or_sell(self):
        """direction must be 'BUY' or 'SELL'."""
        with pytest.raises(ValidationError) as exc_info:
            EntryPlan(
                planner_id="test",
                symbol="BTCUSDT",
                direction="HOLD",  # type: ignore[arg-type]  # Invalid direction
                order_type="MARKET",
                timing="IMMEDIATE",
                rationale="Test"
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("direction",) for e in errors)

    def test_requires_order_type(self):
        """order_type is required."""
        with pytest.raises(ValidationError) as exc_info:
            EntryPlan(
                planner_id="test",
                symbol="BTCUSDT",
                direction="BUY",
                timing="IMMEDIATE",
                rationale="Test"
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("order_type",) for e in errors)

    def test_requires_timing(self):
        """timing is required."""
        with pytest.raises(ValidationError) as exc_info:
            EntryPlan(
                planner_id="test",
                symbol="BTCUSDT",
                direction="BUY",
                order_type="MARKET",
                rationale="Test"
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("timing",) for e in errors)

    def test_requires_rationale(self):
        """rationale is required."""
        with pytest.raises(ValidationError) as exc_info:
            EntryPlan(
                planner_id="test",
                symbol="BTCUSDT",
                direction="BUY",
                order_type="MARKET",
                timing="IMMEDIATE"
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("rationale",) for e in errors)

    def test_max_slippage_must_be_between_0_and_1(self):
        """max_slippage_pct must be in [0.0, 1.0] range."""
        # Too high
        with pytest.raises(ValidationError):
            EntryPlan(
                planner_id="test",
                symbol="BTCUSDT",
                direction="BUY",
                order_type="MARKET",
                timing="IMMEDIATE",
                max_slippage_pct=Decimal("1.5"),  # type: ignore[call-arg]  # Invalid slippage
                rationale="Test"
            )

        # Negative
        with pytest.raises(ValidationError):
            EntryPlan(
                planner_id="test",
                symbol="BTCUSDT",
                direction="BUY",
                order_type="MARKET",
                timing="IMMEDIATE",
                max_slippage_pct=Decimal("-0.1"),  # type: ignore[call-arg]  # Invalid slippage
                rationale="Test"
            )

        # Valid boundaries
        plan_zero = EntryPlan(
            planner_id="test",
            symbol="BTCUSDT",
            direction="BUY",
            order_type="MARKET",
            timing="IMMEDIATE",
            max_slippage_pct=Decimal("0.0"),
            rationale="Test"
        )
        assert plan_zero.max_slippage_pct == Decimal("0.0")

        plan_one = EntryPlan(
            planner_id="test",
            symbol="BTCUSDT",
            direction="BUY",
            order_type="MARKET",
            timing="IMMEDIATE",
            max_slippage_pct=Decimal("1.0"),
            rationale="Test"
        )
        assert plan_one.max_slippage_pct == Decimal("1.0")


class TestEntryPlanDefaultValues:
    """Test EntryPlan default value behavior."""

    def test_auto_generates_plan_id(self):
        """plan_id is auto-generated with ENT_ prefix."""
        plan1 = EntryPlan(
            planner_id="test",
            symbol="BTCUSDT",
            direction="BUY",
            order_type="MARKET",
            timing="IMMEDIATE",
            rationale="Test"
        )
        plan2 = EntryPlan(
            planner_id="test",
            symbol="BTCUSDT",
            direction="BUY",
            order_type="MARKET",
            timing="IMMEDIATE",
            rationale="Test"
        )

        # Check unique plan IDs
        plan1_id = str(plan1.plan_id)
        plan2_id = str(plan2.plan_id)
        assert plan1_id.startswith("ENT_")
        assert plan2_id.startswith("ENT_")
        assert plan1_id != plan2_id

    def test_auto_sets_created_at(self):
        """created_at is auto-set to current UTC time."""
        before = datetime.now(timezone.utc)
        plan = EntryPlan(
            planner_id="test",
            symbol="BTCUSDT",
            direction="BUY",
            order_type="MARKET",
            timing="IMMEDIATE",
            rationale="Test"
        )
        after = datetime.now(timezone.utc)

        assert before <= plan.created_at <= after
        # Verify timezone-aware datetime
        created_at = plan.created_at
        assert isinstance(created_at, datetime)
        # Pylance limitation: FieldInfo doesn't narrow to datetime after isinstance()
        # Runtime works perfectly. See agent.md section 6.6.5 "Bekende acceptable warnings #2"
        tzinfo = created_at.tzinfo  # type: ignore[attr-defined]
        assert tzinfo is not None

    def test_optional_fields_default_to_none(self):
        """Optional fields default to None."""
        plan = EntryPlan(
            planner_id="test",
            symbol="BTCUSDT",
            direction="BUY",
            order_type="MARKET",
            timing="IMMEDIATE",
            rationale="Test"
        )

        assert plan.reference_price is None
        assert plan.limit_price is None
        assert plan.stop_price is None
        assert plan.max_slippage_pct is None
        assert plan.valid_until is None

    def test_planner_metadata_defaults_to_empty_dict(self):
        """planner_metadata defaults to empty dict."""
        plan = EntryPlan(
            planner_id="test",
            symbol="BTCUSDT",
            direction="BUY",
            order_type="MARKET",
            timing="IMMEDIATE",
            rationale="Test"
        )

        assert plan.planner_metadata == {}
        assert isinstance(plan.planner_metadata, dict)


class TestEntryPlanSerialization:
    """Test EntryPlan serialization."""

    def test_can_serialize_to_dict(self):
        """Can serialize EntryPlan to dict."""
        plan = EntryPlan(
            planner_id="test_planner",
            symbol="BTCUSDT",
            direction="BUY",
            order_type="MARKET",
            timing="IMMEDIATE",
            reference_price=Decimal("95000.00"),
            rationale="Test entry"
        )

        data = plan.model_dump()

        assert data["planner_id"] == "test_planner"
        assert data["symbol"] == "BTCUSDT"
        assert data["direction"] == "BUY"
        assert data["order_type"] == "MARKET"
        assert data["reference_price"] == Decimal("95000.00")

    def test_can_serialize_to_json(self):
        """Can serialize EntryPlan to JSON."""
        plan = EntryPlan(
            planner_id="test_planner",
            symbol="BTCUSDT",
            direction="BUY",
            order_type="MARKET",
            timing="IMMEDIATE",
            rationale="Test entry"
        )

        json_str = plan.model_dump_json()

        assert isinstance(json_str, str)
        assert "test_planner" in json_str
        assert "BTCUSDT" in json_str

    def test_can_deserialize_from_dict(self):
        """Can deserialize EntryPlan from dict."""
        data = {
            "plan_id": "ENT_test-123",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "planner_id": "test_planner",
            "symbol": "BTCUSDT",
            "direction": "BUY",
            "order_type": "MARKET",
            "timing": "IMMEDIATE",
            "rationale": "Test entry"
        }

        plan = EntryPlan.model_validate(data)

        assert plan.plan_id == "ENT_test-123"
        assert plan.planner_id == "test_planner"
        assert plan.symbol == "BTCUSDT"


class TestEntryPlanUseCases:
    """Test real-world EntryPlan use cases."""

    def test_immediate_market_order_for_urgent_signal(self):
        """Immediate market entry for high urgency signal."""
        plan = EntryPlan(
            planner_id="immediate_market_entry",
            symbol="BTCUSDT",
            direction="BUY",
            order_type="MARKET",
            timing="IMMEDIATE",
            reference_price=Decimal("95500.00"),
            max_slippage_pct=Decimal("0.001"),  # 0.1% max slippage
            rationale="High confidence breakout signal with urgency=0.95"
        )

        assert plan.order_type == "MARKET"
        assert plan.timing == "IMMEDIATE"
        assert plan.max_slippage_pct == Decimal("0.001")

    def test_layered_entry_for_large_position(self):
        """Layered limit entry for reducing market impact."""
        plan = EntryPlan(
            planner_id="layered_limit_entry",
            symbol="ETHUSDT",
            direction="BUY",
            order_type="LIMIT",
            timing="LAYERED",
            reference_price=Decimal("3500.00"),
            limit_price=Decimal("3495.00"),
            planner_metadata={
                "layers": 5,
                "layer_spacing_pct": "0.0025",
                "total_position_value": "100000"
            },
            rationale="Large position requires layered entry to avoid slippage"
        )

        assert plan.timing == "LAYERED"
        assert plan.planner_metadata["layers"] == 5

    def test_patient_limit_entry_for_optimal_price(self):
        """Patient limit entry waiting for better price."""
        valid_until = datetime.now(timezone.utc) + timedelta(hours=4)

        plan = EntryPlan(
            planner_id="patient_limit_entry",
            symbol="SOLUSDT",
            direction="SELL",
            order_type="LIMIT",
            timing="PATIENT",
            reference_price=Decimal("120.00"),
            limit_price=Decimal("121.50"),
            valid_until=valid_until,
            rationale="Low urgency signal, can wait for optimal price"
        )

        assert plan.timing == "PATIENT"
        assert plan.valid_until is not None
        # Selling above reference price
        assert plan.limit_price is not None
        assert plan.reference_price is not None
        assert plan.limit_price > plan.reference_price

    def test_twap_entry_for_time_distributed_execution(self):
        """TWAP entry for time-weighted execution."""
        plan = EntryPlan(
            planner_id="twap_entry",
            symbol="BTCUSDT",
            direction="BUY",
            order_type="LIMIT",
            timing="TWAP",
            reference_price=Decimal("95000.00"),
            planner_metadata={
                "twap_duration_minutes": 60,
                "twap_intervals": 12,
                "adaptive_pricing": True
            },
            rationale="Time-weighted average price over 1 hour"
        )

        assert plan.timing == "TWAP"
        assert plan.planner_metadata["twap_duration_minutes"] == 60
