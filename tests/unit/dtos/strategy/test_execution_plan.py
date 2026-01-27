"""
Unit tests for ExecutionPlan DTO.

STAP 1 RED: Write 15+ FAILING tests based on execution_plan_DESIGN.md
Expected: ALL RED until DTO implementation (STAP 2)

Test Categories:
- Creation Tests (3): minimal, full, with hints
- Validation Tests (6): urgency/visibility/slippage ranges
- Action Tests (4): execute/cancel/modify/cancel_group
- Immutability Tests (2): frozen, replace
- JSON Serialization (1): roundtrip
"""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.dtos.strategy.execution_plan import ExecutionAction, ExecutionPlan


class TestExecutionPlanCreation:
    """Test ExecutionPlan creation with various field combinations."""

    def test_execution_plan_creation_minimal(self):
        """Test creation with only required fields."""
        intent = ExecutionPlan(
            plan_id="EXP_20251028_143022_a8f3c",
            action=ExecutionAction.EXECUTE_TRADE,
            execution_urgency=Decimal("0.82"),
            visibility_preference=Decimal("0.20"),
            max_slippage_pct=Decimal("0.0100")
        )

        assert intent.plan_id == "EXP_20251028_143022_a8f3c"
        assert intent.action == ExecutionAction.EXECUTE_TRADE
        assert intent.execution_urgency == Decimal("0.82")
        assert intent.visibility_preference == Decimal("0.20")
        assert intent.max_slippage_pct == Decimal("0.0100")

        # Defaults for optional fields
        assert intent.must_complete_immediately is False
        assert intent.max_execution_window_minutes is None
        assert intent.preferred_execution_style is None
        assert intent.chunk_count_hint is None
        assert intent.chunk_distribution is None
        assert intent.min_fill_ratio is None

    def test_execution_plan_creation_full(self):
        """Test creation with all fields populated."""
        intent = ExecutionPlan(
            plan_id="EXP_20251028_143025_b7c4d",
            action=ExecutionAction.EXECUTE_TRADE,
            execution_urgency=Decimal("0.20"),
            visibility_preference=Decimal("0.10"),
            max_slippage_pct=Decimal("0.0050"),
            must_complete_immediately=False,
            max_execution_window_minutes=30,
            preferred_execution_style="TWAP",
            chunk_count_hint=5,
            chunk_distribution="UNIFORM",
            min_fill_ratio=Decimal("0.80")
        )

        assert intent.plan_id == "EXP_20251028_143025_b7c4d"
        assert intent.action == ExecutionAction.EXECUTE_TRADE
        assert intent.execution_urgency == Decimal("0.20")
        assert intent.visibility_preference == Decimal("0.10")
        assert intent.max_slippage_pct == Decimal("0.0050")
        assert intent.must_complete_immediately is False
        assert intent.max_execution_window_minutes == 30
        assert intent.preferred_execution_style == "TWAP"
        assert intent.chunk_count_hint == 5
        assert intent.chunk_distribution == "UNIFORM"
        assert intent.min_fill_ratio == Decimal("0.80")

    def test_execution_plan_creation_with_hints(self):
        """Test creation with optional hints only."""
        intent = ExecutionPlan(
            plan_id="EXP_20251028_143030_c8e6f",
            action=ExecutionAction.EXECUTE_TRADE,
            execution_urgency=Decimal("0.50"),
            visibility_preference=Decimal("0.30"),
            max_slippage_pct=Decimal("0.0075"),
            preferred_execution_style="VWAP",
            chunk_count_hint=10
        )

        assert intent.preferred_execution_style == "VWAP"
        assert intent.chunk_count_hint == 10
        assert intent.chunk_distribution is None  # Not set
        assert intent.min_fill_ratio is None  # Not set


class TestExecutionPlanValidation:
    """Test field validation rules."""

    def test_urgency_validation_in_range(self):
        """Test urgency accepts valid range 0.0-1.0."""
        # Boundary values
        intent_min = ExecutionPlan(
            plan_id="EXP_20251028_143035_d9a7f",
            action=ExecutionAction.EXECUTE_TRADE,
            execution_urgency=Decimal("0.0"),  # Min valid
            visibility_preference=Decimal("0.5"),
            max_slippage_pct=Decimal("0.01")
        )
        assert intent_min.execution_urgency == Decimal("0.0")

        intent_max = ExecutionPlan(
            plan_id="EXP_20251028_143040_e1b8g",
            action=ExecutionAction.EXECUTE_TRADE,
            execution_urgency=Decimal("1.0"),  # Max valid
            visibility_preference=Decimal("0.5"),
            max_slippage_pct=Decimal("0.01")
        )
        assert intent_max.execution_urgency == Decimal("1.0")

        # Mid-range
        intent_mid = ExecutionPlan(
            plan_id="EXP_20251028_143045_f2c9h",
            action=ExecutionAction.EXECUTE_TRADE,
            execution_urgency=Decimal("0.5"),
            visibility_preference=Decimal("0.5"),
            max_slippage_pct=Decimal("0.01")
        )
        assert intent_mid.execution_urgency == Decimal("0.5")

    def test_urgency_validation_out_of_range(self):
        """Test urgency rejects values outside 0.0-1.0."""
        # Below minimum
        with pytest.raises(ValidationError):
            ExecutionPlan(
                plan_id="EXP_20251028_143050_g3d0i",
                action=ExecutionAction.EXECUTE_TRADE,
                execution_urgency=Decimal("-0.1"),  # Invalid
                visibility_preference=Decimal("0.5"),
                max_slippage_pct=Decimal("0.01")
            )

        # Above maximum
        with pytest.raises(ValidationError):
            ExecutionPlan(
                plan_id="EXP_20251028_143055_h4e1j",
                action=ExecutionAction.EXECUTE_TRADE,
                execution_urgency=Decimal("1.5"),  # Invalid
                visibility_preference=Decimal("0.5"),
                max_slippage_pct=Decimal("0.01")
            )

    def test_visibility_validation_in_range(self):
        """Test visibility accepts valid range 0.0-1.0."""
        # Boundary values
        intent_min = ExecutionPlan(
            plan_id="EXP_20251028_144000_i5f2k",
            action=ExecutionAction.EXECUTE_TRADE,
            execution_urgency=Decimal("0.5"),
            visibility_preference=Decimal("0.0"),  # Min valid
            max_slippage_pct=Decimal("0.01")
        )
        assert intent_min.visibility_preference == Decimal("0.0")

        intent_max = ExecutionPlan(
            plan_id="EXP_20251028_144005_j6g3l",
            action=ExecutionAction.EXECUTE_TRADE,
            execution_urgency=Decimal("0.5"),
            visibility_preference=Decimal("1.0"),  # Max valid
            max_slippage_pct=Decimal("0.01")
        )
        assert intent_max.visibility_preference == Decimal("1.0")

    def test_visibility_validation_out_of_range(self):
        """Test visibility rejects values outside 0.0-1.0."""
        with pytest.raises(ValidationError):
            ExecutionPlan(
                plan_id="EXP_20251028_144010_k7h4m",
                action=ExecutionAction.EXECUTE_TRADE,
                execution_urgency=Decimal("0.5"),
                visibility_preference=Decimal("2.0"),  # Invalid
                max_slippage_pct=Decimal("0.01")
            )

    def test_slippage_validation_in_range(self):
        """Test slippage accepts valid range 0.0-1.0."""
        # Zero slippage (valid for backtests)
        intent_zero = ExecutionPlan(
            plan_id="EXP_20251028_144015_l8i5n",
            action=ExecutionAction.EXECUTE_TRADE,
            execution_urgency=Decimal("0.5"),
            visibility_preference=Decimal("0.5"),
            max_slippage_pct=Decimal("0.0")  # Valid
        )
        assert intent_zero.max_slippage_pct == Decimal("0.0")

        # Normal slippage
        intent_normal = ExecutionPlan(
            plan_id="EXP_20251028_144020_m9j6o",
            action=ExecutionAction.EXECUTE_TRADE,
            execution_urgency=Decimal("0.5"),
            visibility_preference=Decimal("0.5"),
            max_slippage_pct=Decimal("0.0200")  # 2%
        )
        assert intent_normal.max_slippage_pct == Decimal("0.0200")

    def test_slippage_validation_out_of_range(self):
        """Test slippage rejects values outside 0.0-1.0."""
        with pytest.raises(ValidationError):
            ExecutionPlan(
                plan_id="EXP_20251028_144025_n0k7p",
                action=ExecutionAction.EXECUTE_TRADE,
                execution_urgency=Decimal("0.5"),
                visibility_preference=Decimal("0.5"),
                max_slippage_pct=Decimal("1.5")  # Invalid (150%!)
            )


class TestExecutionPlanActions:
    """Test different action types."""

    def test_action_execute_trade(self):
        """Test EXECUTE_TRADE action."""
        intent = ExecutionPlan(
            plan_id="EXP_20251028_144030_o1l8q",
            action=ExecutionAction.EXECUTE_TRADE,
            execution_urgency=Decimal("0.90"),
            visibility_preference=Decimal("0.70"),
            max_slippage_pct=Decimal("0.0100")
        )

        assert intent.action == ExecutionAction.EXECUTE_TRADE
        assert isinstance(intent.action, ExecutionAction)

    def test_action_cancel_order(self):
        """Test CANCEL_ORDER action."""
        intent = ExecutionPlan(
            plan_id="EXP_20251028_144035_p2m9r",
            action=ExecutionAction.CANCEL_ORDER,
            execution_urgency=Decimal("1.0"),  # Max urgency for cancel
            visibility_preference=Decimal("0.5"),
            max_slippage_pct=Decimal("0.0")  # N/A for cancel
        )

        assert intent.action == ExecutionAction.CANCEL_ORDER

    def test_action_cancel_group(self):
        """Test CANCEL_GROUP action (cancel entire TWAP)."""
        intent = ExecutionPlan(
            plan_id="EXP_20251028_144040_q3n0s",
            action=ExecutionAction.CANCEL_GROUP,
            execution_urgency=Decimal("1.0"),  # Emergency cancel
            visibility_preference=Decimal("0.5"),
            max_slippage_pct=Decimal("0.0"),
            must_complete_immediately=True
        )

        assert intent.action == ExecutionAction.CANCEL_GROUP
        assert intent.must_complete_immediately is True

    def test_action_modify_order(self):
        """Test MODIFY_ORDER action."""
        intent = ExecutionPlan(
            plan_id="EXP_20251028_144045_r4o1t",
            action=ExecutionAction.MODIFY_ORDER,
            execution_urgency=Decimal("0.60"),
            visibility_preference=Decimal("0.40"),
            max_slippage_pct=Decimal("0.0050")
        )

        assert intent.action == ExecutionAction.MODIFY_ORDER


class TestExecutionPlanImmutability:
    """Test immutability (frozen Pydantic model)."""

    def test_immutability_frozen(self):
        """Test that ExecutionPlan cannot be mutated after creation."""
        intent = ExecutionPlan(
            plan_id="EXP_20251028_144050_s5p2u",
            action=ExecutionAction.EXECUTE_TRADE,
            execution_urgency=Decimal("0.50"),
            visibility_preference=Decimal("0.30"),
            max_slippage_pct=Decimal("0.0075")
        )

        # Attempt to mutate should raise ValidationError (Pydantic frozen)
        with pytest.raises(ValidationError):
            intent.execution_urgency = Decimal("0.90")

        with pytest.raises(ValidationError):
            intent.must_complete_immediately = True

    def test_immutability_replace(self):
        """Test that model_copy() creates new instance."""
        original = ExecutionPlan(
            plan_id="EXP_20251028_144055_t6q3v",
            action=ExecutionAction.EXECUTE_TRADE,
            execution_urgency=Decimal("0.50"),
            visibility_preference=Decimal("0.30"),
            max_slippage_pct=Decimal("0.0075")
        )

        # Create new instance with modified urgency (Pydantic model_copy)
        updated = original.model_copy(
            update={"execution_urgency": Decimal("0.90")}
        )

        # Original unchanged
        assert original.execution_urgency == Decimal("0.50")

        # New instance has updated value
        assert updated.execution_urgency == Decimal("0.90")

        # Other fields unchanged
        assert updated.visibility_preference == Decimal("0.30")
        assert updated.max_slippage_pct == Decimal("0.0075")

        # Different objects
        assert original is not updated


class TestExecutionPlanSerialization:  # pylint: disable=too-few-public-methods
    """Test JSON serialization."""

    def test_json_serialization_roundtrip(self):
        """Test model_dump() → model_validate() roundtrip (Pydantic)."""
        original = ExecutionPlan(
            plan_id="EXP_20251028_145000_u7r4w",
            action=ExecutionAction.EXECUTE_TRADE,
            execution_urgency=Decimal("0.82"),
            visibility_preference=Decimal("0.20"),
            max_slippage_pct=Decimal("0.0100"),
            must_complete_immediately=False,
            max_execution_window_minutes=30,
            preferred_execution_style="TWAP",
            chunk_count_hint=5,
            chunk_distribution="UNIFORM",
            min_fill_ratio=Decimal("0.80")
        )

        # Serialize to dict (Pydantic model_dump)
        data = original.model_dump()

        assert data["plan_id"] == "EXP_20251028_145000_u7r4w"
        assert data["action"] == "EXECUTE_TRADE"
        assert data["execution_urgency"] == Decimal("0.82")
        assert data["visibility_preference"] == Decimal("0.20")
        assert data["max_slippage_pct"] == Decimal("0.0100")
        assert data["preferred_execution_style"] == "TWAP"
        assert data["chunk_count_hint"] == 5

        # Deserialize from dict (Pydantic model_validate)
        restored = ExecutionPlan.model_validate(data)

        assert restored.plan_id == original.plan_id
        assert restored.action == original.action
        assert restored.execution_urgency == original.execution_urgency
        assert restored.visibility_preference == original.visibility_preference
        assert restored.max_slippage_pct == original.max_slippage_pct
        assert restored.preferred_execution_style == original.preferred_execution_style
        assert restored.chunk_count_hint == original.chunk_count_hint
        assert restored.chunk_distribution == original.chunk_distribution
        assert restored.min_fill_ratio == original.min_fill_ratio


class TestExecutionPlanEdgeCases:
    """Test edge cases and special scenarios."""

    def test_high_urgency_immediate_constraint(self):
        """Test high urgency with immediate completion constraint."""
        intent = ExecutionPlan(
            plan_id="EXP_20251028_145005_v8s5x",
            action=ExecutionAction.EXECUTE_TRADE,
            execution_urgency=Decimal("0.95"),  # Very high
            visibility_preference=Decimal("0.70"),
            max_slippage_pct=Decimal("0.0200"),  # Willing to pay for speed
            must_complete_immediately=True
        )

        assert intent.execution_urgency == Decimal("0.95")
        assert intent.must_complete_immediately is True
        assert intent.max_execution_window_minutes is None  # Should be None

    def test_low_urgency_with_execution_window(self):
        """Test low urgency with time window (patient TWAP)."""
        intent = ExecutionPlan(
            plan_id="EXP_20251028_145010_w9t6y",
            action=ExecutionAction.EXECUTE_TRADE,
            execution_urgency=Decimal("0.15"),  # Very patient
            visibility_preference=Decimal("0.05"),  # Maximum stealth
            max_slippage_pct=Decimal("0.0030"),  # Tight slippage
            must_complete_immediately=False,
            max_execution_window_minutes=60,  # 1 hour window
            preferred_execution_style="TWAP",
            chunk_count_hint=20  # Many small chunks
        )

        assert intent.execution_urgency == Decimal("0.15")
        assert intent.max_execution_window_minutes == 60
        assert intent.preferred_execution_style == "TWAP"
        assert intent.chunk_count_hint == 20

    def test_zero_slippage_for_backtest(self):
        """Test zero slippage tolerance (backtest exact fills)."""
        intent = ExecutionPlan(
            plan_id="EXP_20251028_145015_x0u7z",
            action=ExecutionAction.EXECUTE_TRADE,
            execution_urgency=Decimal("0.50"),
            visibility_preference=Decimal("0.50"),
            max_slippage_pct=Decimal("0.0")  # Exact fills only
        )

        assert intent.max_slippage_pct == Decimal("0.0")


# Test count: 18 tests total
# - 3 creation tests
# - 6 validation tests
# - 4 action tests
# - 2 immutability tests
# - 1 serialization test
# - 3 edge case tests (bonus)
#
# Expected result: ALL RED ❌ until ExecutionPlan DTO implemented

