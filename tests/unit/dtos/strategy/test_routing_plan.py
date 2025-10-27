# tests/unit/dtos/strategy/test_routing_plan.py
"""
Unit tests for RoutingPlan DTO - HOW/WHEN execution specification.

Tests the lean RoutingPlan DTO which specifies HOW and WHEN to execute
orders (timing strategy, urgency, slippage tolerance).

**Lean Spec Philosophy:**
- HOW/WHEN: timing, time_in_force, max_slippage_pct, execution_urgency
- NO TWAP params (platform-specific config, not DTO spec)
- NO metadata, timestamps, causality (sub-planners don't track)

@layer: Tests (Unit - Strategy DTOs)
@dependencies: [pytest, decimal, backend.dtos.strategy.routing_plan]
"""

import re
from decimal import Decimal
import pytest

from backend.dtos.strategy.routing_plan import RoutingPlan


class TestRoutingPlanCreation:
    """Test RoutingPlan DTO creation with valid data."""

    def test_create_routing_plan_immediate(self):
        """Test creating RoutingPlan with IMMEDIATE timing."""
        plan = RoutingPlan(
            timing="IMMEDIATE",
            time_in_force="GTC",
            max_slippage_pct=Decimal("0.5"),
            execution_urgency=Decimal("0.8"),
            iceberg_preference=False
        )

        assert getattr(plan, "plan_id").startswith("ROU_")
        assert plan.timing == "IMMEDIATE"
        assert plan.time_in_force == "GTC"
        assert plan.max_slippage_pct == Decimal("0.5")
        assert plan.execution_urgency == Decimal("0.8")
        assert plan.iceberg_preference is False

    def test_create_routing_plan_twap(self):
        """Test creating RoutingPlan with TWAP timing."""
        plan = RoutingPlan(
            timing="TWAP",
            time_in_force="GTC",
            max_slippage_pct=Decimal("0.2"),
            execution_urgency=Decimal("0.3"),
            iceberg_preference=True
        )

        assert plan.timing == "TWAP"
        assert plan.iceberg_preference is True

    def test_create_routing_plan_patient(self):
        """Test creating RoutingPlan with PATIENT timing."""
        plan = RoutingPlan(
            timing="PATIENT",
            time_in_force="GTC",
            max_slippage_pct=Decimal("0.1"),
            execution_urgency=Decimal("0.1"),
            iceberg_preference=False
        )

        assert plan.timing == "PATIENT"
        assert plan.execution_urgency == Decimal("0.1")

    def test_plan_id_auto_generated(self):
        """Test that plan_id is auto-generated with correct format."""
        plan = RoutingPlan(
            timing="IMMEDIATE",
            time_in_force="GTC",
            max_slippage_pct=Decimal("0.5"),
            execution_urgency=Decimal("0.8")
        )

        # ROU_YYYYMMDD_HHMMSS_hash format
        assert getattr(plan, "plan_id").startswith("ROU_")
        assert len(getattr(plan, "plan_id")) == 28  # ROU_ + 8 + _ + 6 + _ + 8


class TestRoutingPlanValidation:
    """Test RoutingPlan DTO validation rules."""

    def test_timing_must_be_valid_literal(self):
        """Test that timing must be one of allowed values."""
        with pytest.raises(ValueError):
            RoutingPlan(
                timing="INVALID",
                time_in_force="GTC",
                max_slippage_pct=Decimal("0.5"),
                execution_urgency=Decimal("0.8")
            )

    def test_time_in_force_must_be_valid_literal(self):
        """Test that time_in_force must be one of allowed values."""
        with pytest.raises(ValueError):
            RoutingPlan(
                timing="IMMEDIATE",
                time_in_force="INVALID",
                max_slippage_pct=Decimal("0.5"),
                execution_urgency=Decimal("0.8")
            )

    def test_max_slippage_pct_must_be_positive(self):
        """Test that max_slippage_pct must be >= 0."""
        with pytest.raises(ValueError, match="greater than or equal to 0"):
            RoutingPlan(
                timing="IMMEDIATE",
                time_in_force="GTC",
                max_slippage_pct=Decimal("-0.1"),
                execution_urgency=Decimal("0.8")
            )

    def test_max_slippage_pct_reasonable_upper_bound(self):
        """Test that max_slippage_pct has reasonable upper bound."""
        with pytest.raises(ValueError, match="less than or equal to 100"):
            RoutingPlan(
                timing="IMMEDIATE",
                time_in_force="GTC",
                max_slippage_pct=Decimal("101.0"),
                execution_urgency=Decimal("0.8")
            )

    def test_execution_urgency_bounded_0_to_1(self):
        """Test that execution_urgency is bounded [0.0, 1.0]."""
        # Below 0
        with pytest.raises(ValueError, match="greater than or equal to 0"):
            RoutingPlan(
                timing="IMMEDIATE",
                time_in_force="GTC",
                max_slippage_pct=Decimal("0.5"),
                execution_urgency=Decimal("-0.1")
            )

        # Above 1
        with pytest.raises(ValueError, match="less than or equal to 1"):
            RoutingPlan(
                timing="IMMEDIATE",
                time_in_force="GTC",
                max_slippage_pct=Decimal("0.5"),
                execution_urgency=Decimal("1.5")
            )

    def test_all_fields_required(self):
        """Test that all fields are required."""
        with pytest.raises(ValueError):
            RoutingPlan(
                timing="IMMEDIATE"
                # Missing other required fields
            )

    def test_precision_preserved(self):
        """Test that Decimal precision is preserved."""
        plan = RoutingPlan(
            timing="TWAP",
            time_in_force="GTC",
            max_slippage_pct=Decimal("0.12345678"),
            execution_urgency=Decimal("0.87654321")
        )

        assert plan.max_slippage_pct == Decimal("0.12345678")
        assert plan.execution_urgency == Decimal("0.87654321")


class TestRoutingPlanImmutability:
    """Test RoutingPlan DTO immutability."""

    def test_routing_plan_is_frozen(self):
        """Test that RoutingPlan is immutable after creation."""
        plan = RoutingPlan(
            timing="IMMEDIATE",
            time_in_force="GTC",
            max_slippage_pct=Decimal("0.5"),
            execution_urgency=Decimal("0.8")
        )

        with pytest.raises(ValueError, match="frozen"):
            plan.timing = "PATIENT"

    def test_no_extra_fields_allowed(self):
        """Test that extra fields are rejected."""
        with pytest.raises(ValueError):
            RoutingPlan(
                timing="TWAP",
                time_in_force="GTC",
                max_slippage_pct=Decimal("0.5"),
                execution_urgency=Decimal("0.3"),
                twap_duration_seconds=300  # Not allowed in lean spec
            )


class TestRoutingPlanPlanIdFormat:
    """Test RoutingPlan plan_id format validation."""

    def test_plan_id_matches_pattern(self):
        """Test that generated plan_id matches ROU_ pattern."""
        plan = RoutingPlan(
            timing="IMMEDIATE",
            time_in_force="GTC",
            max_slippage_pct=Decimal("0.5"),
            execution_urgency=Decimal("0.8")
        )

        # Should match: ROU_YYYYMMDD_HHMMSS_hash
        pattern = r'^ROU_\d{8}_\d{6}_[0-9a-f]{8}$'
        assert re.match(pattern, plan.plan_id)

    def test_plan_id_uniqueness(self):
        """Test that plan_ids are unique across instances."""
        plan1 = RoutingPlan(
            timing="IMMEDIATE",
            time_in_force="GTC",
            max_slippage_pct=Decimal("0.5"),
            execution_urgency=Decimal("0.8")
        )
        plan2 = RoutingPlan(
            timing="IMMEDIATE",
            time_in_force="GTC",
            max_slippage_pct=Decimal("0.5"),
            execution_urgency=Decimal("0.8")
        )

        # Same data, but different IDs (hash ensures uniqueness)
        assert plan1.plan_id != plan2.plan_id


class TestRoutingPlanIcebergPreferenceDefault:
    """Test RoutingPlan iceberg_preference default value."""

    def test_iceberg_preference_defaults_to_false(self):
        """Test that iceberg_preference defaults to False when omitted."""
        plan = RoutingPlan(
            timing="IMMEDIATE",
            time_in_force="GTC",
            max_slippage_pct=Decimal("0.5"),
            execution_urgency=Decimal("0.8")
        )

        assert plan.iceberg_preference is False
