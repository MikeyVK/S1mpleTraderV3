# tests/unit/dtos/execution/test_execution_directive.py
"""
Unit tests for ExecutionDirective DTO - Final execution instruction.

Tests the ExecutionDirective DTO which aggregates all planning outputs
(Entry, Size, Exit, Execution) into single executable directive.

**Clean Execution Contract:**
- No strategy metadata (clean separation)
- Causality chain with complete ID lineage
- At least 1 plan required (validation)

@layer: Tests (Unit - Execution DTOs)
@dependencies: [
    pytest, backend.dtos.execution.execution_directive,
    backend.dtos.strategy.*, backend.dtos.causality
]
"""

import re
from decimal import Decimal
import pytest

from backend.dtos.causality import CausalityChain
from backend.dtos.strategy import (
    EntryPlan,
    SizePlan,
    ExitPlan,
    ExecutionPlan,
)
from backend.dtos.execution.execution_directive import ExecutionDirective


class TestExecutionDirectiveCreation:
    """Test ExecutionDirective creation with valid data."""

    def test_create_directive_all_plans(self):
        """Test creating directive with all 4 plans (NEW_TRADE scenario)."""
        causality = CausalityChain(tick_id="TCK_20251027_100000_abc123")

        entry = EntryPlan(
            symbol="BTCUSDT",
            direction="BUY",
            order_type="LIMIT",
            limit_price=Decimal("100000.00")
        )
        size = SizePlan(
            position_size=Decimal("0.5"),
            position_value=Decimal("50000.00"),
            risk_amount=Decimal("500.00")
        )
        exit_plan = ExitPlan(
            stop_loss_price=Decimal("95000.00"),
            take_profit_price=Decimal("105000.00")
        )
        execution_plan = ExecutionPlan(
            execution_urgency=Decimal("0.80"),
            visibility_preference=Decimal("0.50"),
            max_slippage_pct=Decimal("0.0050"),
            must_complete_immediately=False
        )

        directive = ExecutionDirective(
            causality=causality,
            entry_plan=entry,
            size_plan=size,
            exit_plan=exit_plan,
            execution_plan=execution_plan
        )

        assert getattr(directive, "directive_id").startswith("EXE_")
        assert directive.causality == causality
        assert directive.entry_plan == entry
        assert directive.size_plan == size
        assert directive.exit_plan == exit_plan
        assert directive.execution_plan == execution_plan
        # Verify ExecutionPlan fields are preserved
        assert directive.execution_plan is not None  # Type narrowing for type checker
        assert directive.execution_plan.execution_urgency == Decimal("0.80")
        assert directive.execution_plan.visibility_preference == Decimal("0.50")
        assert directive.execution_plan.max_slippage_pct == Decimal("0.0050")
        assert directive.execution_plan.must_complete_immediately is False

    def test_create_directive_partial_plans_modify_scenario(self):
        """Test creating directive with partial plans (MODIFY_EXISTING - trailing stop)."""
        causality = CausalityChain(tick_id="TCK_20251027_100000_abc123")

        # Only exit plan - trailing stop adjustment
        exit_plan = ExitPlan(
            stop_loss_price=Decimal("98000.00")
        )

        directive = ExecutionDirective(
            causality=causality,
            exit_plan=exit_plan
        )

        assert getattr(directive, "directive_id").startswith("EXE_")
        assert directive.entry_plan is None
        assert directive.size_plan is None
        assert directive.exit_plan == exit_plan
        assert directive.execution_plan is None

    def test_create_directive_execution_plan_only(self):
        """Test creating directive with ExecutionPlan only (CANCEL_ORDER scenario)."""
        causality = CausalityChain(tick_id="TCK_20251027_100000_abc123")

        # Only execution plan - for non-trade actions like CANCEL_ORDER
        execution_plan = ExecutionPlan(
            action="CANCEL_ORDER",
            execution_urgency=Decimal("1.0"),
            visibility_preference=Decimal("0.50"),
            max_slippage_pct=Decimal("0.0"),
            must_complete_immediately=True
        )

        directive = ExecutionDirective(
            causality=causality,
            execution_plan=execution_plan
        )

        assert getattr(directive, "directive_id").startswith("EXE_")
        assert directive.entry_plan is None
        assert directive.size_plan is None
        assert directive.exit_plan is None
        assert directive.execution_plan == execution_plan
        assert directive.execution_plan is not None  # Type narrowing
        assert directive.execution_plan.action == "CANCEL_ORDER"
        assert directive.execution_plan.must_complete_immediately is True

    def test_directive_id_auto_generated(self):
        """Test that directive_id is auto-generated with correct format."""
        causality = CausalityChain(tick_id="TCK_20251027_100000_abc123")
        entry = EntryPlan(
            symbol="BTCUSDT",
            direction="BUY",
            order_type="MARKET"
        )

        directive = ExecutionDirective(
            causality=causality,
            entry_plan=entry
        )

        # EXE_YYYYMMDD_HHMMSS_hash format
        assert getattr(directive, "directive_id").startswith("EXE_")
        assert len(getattr(directive, "directive_id")) == 28


class TestExecutionDirectiveValidation:
    """Test ExecutionDirective validation rules."""

    def test_at_least_one_plan_required(self):
        """Test that at least one plan is required."""
        causality = CausalityChain(tick_id="TCK_20251027_100000_abc123")

        with pytest.raises(ValueError, match="at least one plan"):
            ExecutionDirective(causality=causality)

    def test_causality_required(self):
        """Test that causality is required."""
        entry = EntryPlan(
            symbol="BTCUSDT",
            direction="BUY",
            order_type="MARKET"
        )

        with pytest.raises(ValueError):
            ExecutionDirective(entry_plan=entry)  # Missing causality

    def test_multiple_plans_combinations_valid(self):
        """Test various valid plan combinations."""
        causality = CausalityChain(tick_id="TCK_20251027_100000_abc123")

        entry = EntryPlan(symbol="BTCUSDT", direction="BUY", order_type="MARKET")
        size = SizePlan(
            position_size=Decimal("0.5"),
            position_value=Decimal("50000"),
            risk_amount=Decimal("500")
        )

        # Entry + Size only
        directive1 = ExecutionDirective(causality=causality, entry_plan=entry, size_plan=size)
        assert directive1.exit_plan is None

        # Entry only
        directive2 = ExecutionDirective(causality=causality, entry_plan=entry)
        assert directive2.size_plan is None


class TestExecutionDirectiveImmutability:
    """Test ExecutionDirective immutability."""

    def test_directive_is_frozen(self):
        """Test that ExecutionDirective is immutable after creation."""
        causality = CausalityChain(tick_id="TCK_20251027_100000_abc123")
        entry = EntryPlan(symbol="BTCUSDT", direction="BUY", order_type="MARKET")

        directive = ExecutionDirective(causality=causality, entry_plan=entry)

        with pytest.raises(ValueError, match="frozen"):
            directive.entry_plan = None  # type: ignore

    def test_no_extra_fields_allowed(self):
        """Test that extra fields are rejected."""
        causality = CausalityChain(tick_id="TCK_20251027_100000_abc123")
        entry = EntryPlan(symbol="BTCUSDT", direction="BUY", order_type="MARKET")

        with pytest.raises(ValueError):
            ExecutionDirective(
                causality=causality,
                entry_plan=entry,
                strategy_metadata="not allowed"  # Extra field
            )


class TestExecutionDirectiveIdFormat:
    """Test ExecutionDirective directive_id format validation."""

    def test_directive_id_matches_pattern(self):
        """Test that generated directive_id matches EXE_ pattern."""
        causality = CausalityChain(tick_id="TCK_20251027_100000_abc123")
        entry = EntryPlan(symbol="BTCUSDT", direction="BUY", order_type="MARKET")

        directive = ExecutionDirective(causality=causality, entry_plan=entry)

        # Should match: EXE_YYYYMMDD_HHMMSS_hash
        pattern = r'^EXE_\d{8}_\d{6}_[0-9a-f]{8}$'
        assert re.match(pattern, directive.directive_id)

    def test_directive_id_uniqueness(self):
        """Test that directive_ids are unique across instances."""
        causality = CausalityChain(tick_id="TCK_20251027_100000_abc123")
        entry = EntryPlan(symbol="BTCUSDT", direction="BUY", order_type="MARKET")

        directive1 = ExecutionDirective(causality=causality, entry_plan=entry)
        directive2 = ExecutionDirective(causality=causality, entry_plan=entry)

        # Same data, but different IDs (hash ensures uniqueness)
        assert directive1.directive_id != directive2.directive_id


class TestExecutionDirectiveCausalityChain:
    """Test ExecutionDirective causality chain handling."""

    def test_causality_preserved(self):
        """Test that causality chain is preserved in directive."""
        causality = CausalityChain(
            tick_id="TCK_20251027_100000_abc123",
            opportunity_signal_ids=["OPP_20251027_100001_def456"],
            strategy_directive_id="STR_20251027_100002_ghi789"
        )
        entry = EntryPlan(symbol="BTCUSDT", direction="BUY", order_type="MARKET")

        directive = ExecutionDirective(causality=causality, entry_plan=entry)

        # pyright: ignore[reportAttributeAccessIssue] - Pylance false positive
        assert directive.causality.tick_id == "TCK_20251027_100000_abc123"
        assert len(directive.causality.opportunity_signal_ids) == 1
        assert directive.causality.strategy_directive_id == "STR_20251027_100002_ghi789"
