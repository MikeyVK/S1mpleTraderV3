# tests/unit/dtos/strategy/test_exit_plan.py
"""
Unit tests for ExitPlan DTO - WHERE OUT specification.

Tests the lean ExitPlan DTO which specifies WHERE to exit a position
(stop loss and take profit price levels only).

**Lean Spec Philosophy:**
- WHERE OUT: stop_loss_price, take_profit_price (optional)
- NO trailing stops, breakeven logic (PositionMonitor handles)
- NO metadata, timestamps, causality (sub-planners don't track)

@layer: Tests (Unit - Strategy DTOs)
@dependencies: [pytest, decimal, backend.dtos.strategy.exit_plan]
"""

import re
from decimal import Decimal
import pytest

from backend.dtos.strategy.exit_plan import ExitPlan


class TestExitPlanCreation:
    """Test ExitPlan DTO creation with valid data."""

    def test_create_exit_plan_with_both_prices(self):
        """Test creating ExitPlan with both SL and TP."""
        plan = ExitPlan(
            stop_loss_price=Decimal("95000.00"),
            take_profit_price=Decimal("105000.00")
        )

        assert getattr(plan, "plan_id").startswith("EXT_")
        assert plan.stop_loss_price == Decimal("95000.00")
        assert plan.take_profit_price == Decimal("105000.00")

    def test_create_exit_plan_sl_only(self):
        """Test creating ExitPlan with SL only (no TP)."""
        plan = ExitPlan(
            stop_loss_price=Decimal("95000.00")
        )

        assert getattr(plan, "plan_id").startswith("EXT_")
        assert plan.stop_loss_price == Decimal("95000.00")
        assert plan.take_profit_price is None

    def test_plan_id_auto_generated(self):
        """Test that plan_id is auto-generated with correct format."""
        plan = ExitPlan(
            stop_loss_price=Decimal("95000.00")
        )

        # EXT_YYYYMMDD_HHMMSS_hash format
        assert getattr(plan, "plan_id").startswith("EXT_")
        assert len(getattr(plan, "plan_id")) == 28  # EXT_ + 8 + _ + 6 + _ + 8


class TestExitPlanValidation:
    """Test ExitPlan DTO validation rules."""

    def test_stop_loss_price_must_be_positive(self):
        """Test that stop_loss_price must be > 0."""
        with pytest.raises(ValueError, match="greater than 0"):
            ExitPlan(
                stop_loss_price=Decimal("0.00")
            )

        with pytest.raises(ValueError, match="greater than 0"):
            ExitPlan(
                stop_loss_price=Decimal("-100.00")
            )

    def test_take_profit_price_must_be_positive_if_set(self):
        """Test that take_profit_price must be > 0 when provided."""
        with pytest.raises(ValueError, match="greater than 0"):
            ExitPlan(
                stop_loss_price=Decimal("95000.00"),
                take_profit_price=Decimal("0.00")
            )

        with pytest.raises(ValueError, match="greater than 0"):
            ExitPlan(
                stop_loss_price=Decimal("95000.00"),
                take_profit_price=Decimal("-1000.00")
            )

    def test_stop_loss_required(self):
        """Test that stop_loss_price is required."""
        with pytest.raises(ValueError):
            ExitPlan()  # Missing required field

    def test_precision_preserved(self):
        """Test that Decimal precision is preserved."""
        plan = ExitPlan(
            stop_loss_price=Decimal("95000.12345678"),
            take_profit_price=Decimal("105000.87654321")
        )

        assert plan.stop_loss_price == Decimal("95000.12345678")
        assert plan.take_profit_price == Decimal("105000.87654321")


class TestExitPlanImmutability:
    """Test ExitPlan DTO immutability."""

    def test_exit_plan_is_frozen(self):
        """Test that ExitPlan is immutable after creation."""
        plan = ExitPlan(
            stop_loss_price=Decimal("95000.00"),
            take_profit_price=Decimal("105000.00")
        )

        with pytest.raises(ValueError, match="frozen"):
            plan.stop_loss_price = Decimal("96000.00")

    def test_no_extra_fields_allowed(self):
        """Test that extra fields are rejected."""
        with pytest.raises(ValueError):
            ExitPlan(
                stop_loss_price=Decimal("95000.00"),
                trailing_stop=True  # Not allowed in lean spec
            )


class TestExitPlanPlanIdFormat:
    """Test ExitPlan plan_id format validation."""

    def test_plan_id_matches_pattern(self):
        """Test that generated plan_id matches EXT_ pattern."""
        plan = ExitPlan(
            stop_loss_price=Decimal("95000.00")
        )

        # Should match: EXT_YYYYMMDD_HHMMSS_hash
        pattern = r'^EXT_\d{8}_\d{6}_[0-9a-f]{8}$'
        assert re.match(pattern, plan.plan_id)

    def test_plan_id_uniqueness(self):
        """Test that plan_ids are unique across instances."""
        plan1 = ExitPlan(stop_loss_price=Decimal("95000.00"))
        plan2 = ExitPlan(stop_loss_price=Decimal("95000.00"))

        # Same data, but different IDs (hash ensures uniqueness)
        assert plan1.plan_id != plan2.plan_id
